import os
import random

import pygame

import settings
from memory import Memory
from names import random_name

from ...all_needed.base_entity import LivingEntity
from ...all_needed.safe_io import write_json_atomic
from . import ci_info, ci_settings
from .ai import CreatureBrain
from .interactions import CreatureInteractions
from .life_cycle import CreatureAging, CreatureFamily, CreatureTerritory
from .mechanics.input_events import (
    apply_name_edit as _apply_name_edit,
)
from .mechanics.input_events import (
    handle_corpse_release as _handle_corpse_release,
)
from .mechanics.input_events import (
    start_corpse_grab as _start_corpse_grab,
)
from .physiology import CirclePathfinder, CreatureNeeds
from .player_reactions import PlayerReactionHandler
from .psyche import CreaturePsyche
from .social import CreatureCommunication, CreatureSocial

from .state.puberty_state import PubertyState
from .state.burial_state import BurialState
from .state.child_road_play_state import ChildRoadPlayState
from .state.road_verify_state import RoadVerifyState
from .state.construction_state import ConstructionState
from .state.resource_carry_state import ResourceCarryState
from .state.housing_state import HousingState
from .state.elder_care_state import ElderCareState
from .state.road_state import RoadState
from .state.landmark_state import LandmarkState
from .state.ai_state import AIState
from .state.needs_seeking_state import NeedsSeekingState
from .state.sleep_state import SleepState
from .state.awareness_state import AwarenessState
from .state.player_reaction_state import PlayerReactionState
from .state.child_behavior_state import ChildBehaviorState
from .state.social_state import SocialState

class Creature(LivingEntity):
    race_name = ci_settings.RACE_NAME
    diet = ci_settings.RACE_DIET
    food_category_map = ci_settings.RACE_FOOD_CATEGORY_MAP

    def __init__(self, creature_id, name=None, temperament=None, gender=None, name_pools=None):
        # =====================================================================
        # Идентификация
        # =====================================================================
        self.id = creature_id
        self.gender = gender if gender in ci_settings.GENDER_LIST else random.choice(ci_settings.GENDER_LIST)
        self.name = name if name else random_name(self.gender, pools=name_pools)
        self.player_named = False

        # =====================================================================
        # Базовые потребности / физическое тело
        # =====================================================================
        self.hp = ci_settings.HP_MAX
        self.hunger = ci_settings.HUNGER_MAX
        self.thirst = ci_settings.THIRST_MAX
        self.consciousness = ci_settings.SANITY_MAX
        self.sanity_decay_timer = ci_settings.SANITY_DECAY_INTERVAL
        self.energy = ci_settings.ENERGY_MAX
        self.x = random.uniform(50, settings.WORLD_WIDTH - 50)
        self.y = random.uniform(50, settings.WORLD_HEIGHT - 50)
        self.radius = 10
        self.memory = Memory()

        # =====================================================================
        # Текущее состояние / отображаемая цель
        # =====================================================================
        self.state = ci_settings.STATE_CALM
        self.goal_text = ci_info.INFO_CREATURE_STATE_CALM
        self.panic_active = False
        self.is_talking = False

        # =====================================================================
        # Смерть
        # =====================================================================
        self.is_dead = False
        self.death_timer = 0.0
        self.death_cause = None
        self._pending_grief = False

        # =====================================================================
        # Характер / скорость / любопытство
        # =====================================================================
        self.temperament = (temperament if temperament in ci_settings.TEMPERAMENT_LIST
                            else random.choice(ci_settings.TEMPERAMENT_LIST))
        self.base_speed_multiplier = ci_settings.SPEED_MULTIPLIER[self.temperament]
        self.curiosity = random.uniform(*ci_settings.CURIOSITY_RANGE.get(self.temperament, (0.3, 0.6)))

        # =====================================================================
        # Социальные запросы / помощь сородичам
        # =====================================================================
        self.social_state = SocialState()
        self.relationships = {}

        # =====================================================================
        # Ориентиры: зона комфорта / знакомый костёр / место сна
        # =====================================================================
        self.landmarks = LandmarkState.rolled(self.x, self.y)

        # =====================================================================
        # Цель движения / инфраструктура ИИ (троттлинг решений, застревание,
        # заморозка - объединены в AIState, см. state/ai_state.py)
        # =====================================================================
        self.target = None
        self.decision_timer = 0.0
        self.speed_factor = 1.0
        self.ai_state = AIState.rolled(self.x, self.y)

        # =====================================================================
        # Флаги активного поиска базовых нужд (голод/жажда/рассудок)
        # =====================================================================
        self.needs_seeking = NeedsSeekingState()

        # =====================================================================
        # Неуязвимость
        # =====================================================================
        self.spike_invuln_timer = 0.0

        # =====================================================================
        # Осведомлённость: знакомство с типами объектов и цели-воспоминания о еде/воде
        # =====================================================================
        self.awareness = AwarenessState()

        # =====================================================================
        # Глобальная навигация (A* по клеточной карте, creatures/navigation.py)
        # =====================================================================
        self.nav_path = []
        self.nav_path_index = 0
        self.nav_goal = None
        self.nav_recalc_timer = 0.0
        self.nav_search_failed = False

        # =====================================================================
        # Сон
        # =====================================================================
        self.sleep = SleepState.rolled(self.temperament)

        # =====================================================================
        # Отношение к игроку / реакции на прикосновения
        # =====================================================================
        self.player_state = PlayerReactionState()
        self.fear_timer = 0.0
        self.fear_source = None

        # =====================================================================
        # Возраст / стадия жизни
        # =====================================================================
        self.age = 0.0
        self.life_stage = ci_settings.LIFE_STAGE_ADULT

        # =====================================================================
        # Гормональный бум (переходный возраст) и ухаживание
        # =====================================================================
        self.puberty = PubertyState.rolled()

        # =====================================================================
        # Поведение ребёнка: испуг, игры-догонялки
        # =====================================================================
        self.child_behavior = ChildBehaviorState.rolled()

        # =====================================================================
        # Дороги игрока (не детские)
        # =====================================================================
        self.roads = RoadState.rolled()

        # =====================================================================
        # Детские дороги: игра + физическая проверка взрослым
        # =====================================================================
        self.child_road_play = ChildRoadPlayState.rolled()
        self.road_verify = RoadVerifyState.rolled()

        # =====================================================================
        # Опека стариков над случайными детьми
        # =====================================================================
        self.elder_care = ElderCareState.rolled()

        # =====================================================================
        # Труп / кладбище: перенос тела
        # =====================================================================
        self.burial = BurialState()

        # =====================================================================
        # Донашивание ресурсов: кому несём еду/воду + снабжение склада
        # =====================================================================
        self.resources = ResourceCarryState.rolled()

        # =====================================================================
        # Жильё
        # =====================================================================
        self.housing = HousingState()

        # =====================================================================
        # Добыча ресурсов и строительство
        # =====================================================================
        self.construction = ConstructionState.rolled()

        # =====================================================================
        # Специализированные подсистемы
        # =====================================================================
        self.needs = CreatureNeeds(self)
        self.social = CreatureSocial(self)
        self.pathfinder = CirclePathfinder(self)
        self.interactions = CreatureInteractions(self)
        self.player_reactions = PlayerReactionHandler(self)
        self.brain = CreatureBrain(self)
        self.psyche = CreaturePsyche(self)
        self.aging = CreatureAging(self)
        self.communication = CreatureCommunication(self)
        self.family = CreatureFamily(self)
        self.territory = CreatureTerritory(self)

    # =====================================================================
    # Геометрия / общие утилиты
    # =====================================================================

    def carried_total(self):
        return self.construction.carried_resources["wood"] + self.construction.carried_resources["stone"]

    def carry_free_space(self):
        return max(0, self.construction.carry_capacity - self.carried_total())

    def can_handle_corpses(self):
        if self.life_stage == ci_settings.LIFE_STAGE_OLD:
            return True
        if (self.life_stage == ci_settings.LIFE_STAGE_ADULT and self.gender == ci_settings.GENDER_MALE
                and self.temperament != ci_settings.TEMPERAMENT_LAZY):
            return True
        return False

    def can_jump_fences(self):
        if self.life_stage != ci_settings.LIFE_STAGE_ADULT:
            return False
        if self.gender == ci_settings.GENDER_FEMALE and self.family.is_pregnant:
            return False
        return True

    def is_in_own_house(self, houses):
        if self.housing.home_id is None:
            return False
        house = next((h for h in houses if h.id == self.housing.home_id), None)
        if house is None:
            return False
        if self.id not in house.resident_ids:
            return False
        half_w, half_h = house.width / 2, house.height / 2
        return abs(self.x - house.x) <= half_w and abs(self.y - house.y) <= half_h

    def is_hidden(self):
        return not self.is_dead and self.housing.at_home

    def get_type_name(self):
        return ci_info.INFO_CREATURE_KIND

    def commit_name_edit(self, new_name):
        _apply_name_edit(self, new_name)

    def on_grab_start(self, world):
        _start_corpse_grab(self, world)

    def on_grab_release(self, game):
        return _handle_corpse_release(self, game)

    # =====================================================================
    # Реакции на игрока
    # =====================================================================

    def receive_pet(self):
        self.player_reactions.pet()
        self.invalidate_plan()

    def receive_hit(self):
        self.player_reactions.hit()
        self.invalidate_plan()

    def on_marked_favorite(self):
        self.player_reactions.mark_favorite()

    def on_selected_by_player(self):
        self.player_reactions.register_touch()

    def grab_by_player(self):
        self.player_reactions.start_grab()

    def release_by_player(self):
        self.player_reactions.finish_grab()
        self.invalidate_plan()

    # =====================================================================
    # Жизненный цикл
    # =====================================================================

    def die(self, cause):
        self.is_dead = True
        self._pending_grief = True
        self.hp = 0
        self.death_timer = ci_settings.CORPSE_LIFETIME
        self.death_cause = cause
        self.target = None
        self.decision_timer = 0.0
        self.panic_active = False
        self.spike_invuln_timer = 0.0
        self.fear_timer = 0.0
        self.fear_source = None
        self.state = ci_settings.STATE_CALM
        self.goal_text = ci_info.INFO_CREATURE_STATE_DEAD

        self.burial.reset()
        self.construction.reset()
        self.puberty.reset()
        self.resources.reset()
        self.child_road_play.reset()
        self.road_verify.reset()
        self.housing.reset()
        self.family.reset()
        self.elder_care.reset()
        self.roads.reset()
        self.needs_seeking.reset()
        self.ai_state.reset()
        self.player_state.reset()
        self.child_behavior.reset()
        self.social_state.reset()

    def tick_corpse(self, dt):
        return self.needs.tick_corpse(dt)

    # =====================================================================
    # Тонкие делегирующие методы (публичный API не меняется)
    # =====================================================================

    def update_needs(self, dt, other_creatures=None, biome_grid=None):
        self.needs.update(dt, other_creatures, biome_grid)
        self.psyche.update(dt)

    def decide(self, ctx):
        """Троттлинг принятия решений: мозг реально считает раз в
        ci_settings.AI_DECISION_INTERVAL секунд, а не каждый кадр."""
        interval = ci_settings.AI_DECISION_INTERVAL
        if interval <= 0:
            return self.brain.decide(ctx)

        throttle = self.ai_state
        throttle.ai_dt_debt += ctx.dt
        if throttle.ai_plan_valid and throttle.ai_dt_debt < interval:
            return throttle.ai_last_goal

        frame_dt = ctx.dt
        ctx.dt = throttle.ai_dt_debt
        try:
            goal = self.brain.decide(ctx)
        finally:
            ctx.dt = frame_dt

        throttle.ai_dt_debt = 0.0
        throttle.ai_last_goal = goal
        throttle.ai_plan_valid = True
        return goal

    def invalidate_plan(self):
        """Заставить мозг пересчитать решение на ближайшем кадре."""
        self.ai_state.ai_plan_valid = False

    def interact(self, fruits, spikes, water_puddles, bushes, campfires, other_creatures,
                storage_fields, dt, walls=None, biome_grid=None):
        self.interactions.process(fruits, spikes, water_puddles, bushes, campfires,
                                   other_creatures, storage_fields, dt, walls=walls,
                                   biome_grid=biome_grid)

    def effective_vision_radius(self):
        return self.aging.effective_vision_radius()

    def can_verify_child_road_safety(self):
        return self.life_stage == ci_settings.LIFE_STAGE_ADULT

    # =====================================================================
    # Реакция на исчезновение/изменение дорог
    # =====================================================================

    def on_road_deleted(self, road_obj_type, road):
        if road_obj_type == "road":
            if self.roads.on_deleted(road):
                self.invalidate_plan()
            return

        if road_obj_type != "child_road":
            return
        play_matched = self.child_road_play.on_deleted(road)
        verify_matched = self.road_verify.on_deleted(road)
        if play_matched or verify_matched:
            self.roads.following_road_active = False
        self.invalidate_plan()

    def on_road_progress_shift(self, obj_type, road, inserted_index):
        if obj_type == "road":
            self.roads.on_progress_shift(road, inserted_index)
        elif obj_type == "child_road":
            self.child_road_play.on_progress_shift(road, inserted_index)
            self.road_verify.on_progress_shift(road, inserted_index)

    def on_landmark_removed(self, landmark_type, landmark_id, position):
        if landmark_type == "campfire":
            landmarks = self.landmarks
            if landmarks.known_campfire_id == landmark_id or landmarks.known_campfire == position:
                landmarks.known_campfire = None
                landmarks.known_campfire_id = None
            if landmarks.sleep_spot_campfire == position:
                landmarks.sleep_spot_campfire = None
                landmarks.sleep_spot = None
            self.memory.forget_memory("campfire", position[0], position[1])
            self.invalidate_plan()
        elif landmark_type == "graveyard":
            if self.burial.graveyard_target_id == landmark_id:
                self.burial.graveyard_target_id = None
            if self.burial.known_graveyard_id == landmark_id or self.burial.known_graveyard == position:
                self.burial.known_graveyard = None
                self.burial.known_graveyard_id = None
            if self.burial.graveyard_alert_pos == position:
                self.burial.graveyard_alert_pos = None
                self.burial.graveyard_alert_timer = 0.0
            self.memory.forget_memory("graveyard", position[0], position[1])
        elif landmark_type == "water":
            if self.awareness.water_memory_target is not None:
                wx, wy = self.awareness.water_memory_target
                if abs(wx - position[0]) < 8 and abs(wy - position[1]) < 8:
                    self.awareness.water_memory_target = None
            self.memory.forget_memory("water", position[0], position[1])
            self.invalidate_plan()

    # =====================================================================
    # Отрисовка
    # =====================================================================

    def draw_minimap_color(self):
        if self.gender == ci_settings.GENDER_FEMALE:
            return (ci_settings.CREATURE_COLOR_FEMALE_DEAD if self.is_dead
                    else ci_settings.CREATURE_COLOR_FEMALE)
        return ci_settings.CREATURE_COLOR_MALE_DEAD if self.is_dead else ci_settings.CREATURE_COLOR_MALE

    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = screen_pos
        if self.gender == ci_settings.GENDER_FEMALE:
            color = (ci_settings.CREATURE_COLOR_FEMALE_DEAD if self.is_dead
                     else ci_settings.CREATURE_COLOR_FEMALE)
        else:
            color = (ci_settings.CREATURE_COLOR_MALE_DEAD if self.is_dead
                     else ci_settings.CREATURE_COLOR_MALE)

        # ---------- Радиус круга зависит от стадии жизни ----------
        draw_radius = (ci_settings.CHILD_CREATURE_RADIUS
                       if self.life_stage == ci_settings.LIFE_STAGE_CHILD else self.radius)

        pygame.draw.circle(screen, color, (int(sx), int(sy)), draw_radius)

        # ---------- Старики: полая белая окружность внутри основного круга ----------
        if self.life_stage == ci_settings.LIFE_STAGE_OLD:
            inner_radius = max(2, draw_radius - 3)
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), inner_radius, 2)

        # ---------- Хват игрока - индикатор взаимодействия, настройка "кольца" на него не влияет ----------
        if self.player_state.is_grabbed:
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), draw_radius + 4, 2)
        elif show_status_rings:
            if self.player_state.calm_timer > 0:
                pygame.draw.circle(screen, (255, 210, 120), (int(sx), int(sy)), draw_radius + 3, 1)
            elif self.fear_timer > 0:
                pygame.draw.circle(screen, (255, 90, 90), (int(sx), int(sy)), draw_radius + 3, 1)
            elif self.puberty.active:
                pygame.draw.circle(screen, ci_settings.PUBERTY_RING_COLOR,
                                   (int(sx), int(sy)), draw_radius + 3, 1)

    # =====================================================================
    # Сохранение
    # =====================================================================

    def save(self, base_path):
        folder_path = os.path.join(base_path, self.id)
        os.makedirs(folder_path, exist_ok=True)
        state = {
            "id": self.id,
            "race": self.get_race_name(),
            "name": self.name,
            "hp": self.hp,
            "hunger": self.hunger,
            "thirst": self.thirst,
            "consciousness": self.consciousness,
            "energy": self.energy,
            "x": self.x,
            "y": self.y,
            "temperament": self.temperament,
            "is_dead": self.is_dead,
            "death_timer": self.death_timer,
            "death_cause": self.death_cause,
            "relationships": self.relationships,
            "gender": self.gender,
            "age": self.age,
            "curiosity": self.curiosity,
            "fear_timer": self.fear_timer,
            "psyche_joy": self.psyche.joy,
            "psyche_satisfaction": self.psyche.satisfaction,
            "psyche_calmness": self.psyche.calmness,
            "psyche_confidence": self.psyche.confidence,
            "psyche_attachment": self.psyche.attachment,
            **self.puberty.to_persisted_dict(),
            **self.burial.to_persisted_dict(),
            **self.resources.to_persisted_dict(),
            **self.construction.to_persisted_dict(),
            **self.housing.to_persisted_dict(),
            **self.family.to_persisted_dict(),
            **self.elder_care.to_persisted_dict(),
            **self.roads.to_persisted_dict(),
            **self.landmarks.to_persisted_dict(),
            **self.sleep.to_persisted_dict(),
            **self.awareness.to_persisted_dict(),
            **self.player_state.to_persisted_dict(),
        }
        write_json_atomic(os.path.join(folder_path, "state.json"), state, indent=2)
        self.memory.save(os.path.join(folder_path, "memory.json"))

    def release_references(self):
        self.needs = None
        self.social = None
        self.communication = None
        self.pathfinder = None
        self.interactions = None
        self.player_reactions = None
        self.brain = None
        self.psyche = None
        self.aging = None
        self.family = None
        self.territory = None