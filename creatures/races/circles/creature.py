import json
import random
import pygame
import os

import settings
from memory import Memory
from names import random_name

from .ci_settings import *
from .ci_info import *
from .life_cycle import CreatureAging, CreatureTerritory, CreatureFamily
from .physiology import CreatureNeeds, CirclePathfinder
from .social import CreatureSocial, CreatureCommunication
from .interactions import CreatureInteractions
from .player_reactions import PlayerReactionHandler
from .psyche import CreaturePsyche
from .ai import CreatureBrain
from .mechanics.input_events import (
    start_corpse_grab as _start_corpse_grab,
    handle_corpse_release as _handle_corpse_release,
    apply_name_edit as _apply_name_edit,
)

from ...all_needed.base_entity import LivingEntity

class Creature(LivingEntity):
    race_name = "circle"
    diet = RACE_DIET
    food_category_map = RACE_FOOD_CATEGORY_MAP

    def __init__(self, creature_id, name=None, temperament=None, gender=None):
        self.id = creature_id
        self.gender = gender if gender in GENDER_LIST else random.choice(GENDER_LIST)
        self.name = name if name else random_name(self.gender)
        self.player_named = False
        self.hp = HP_MAX
        self.hunger = HUNGER_MAX
        self.thirst = THIRST_MAX
        self.consciousness = SANITY_MAX
        self.sanity_decay_timer = SANITY_DECAY_INTERVAL
        self.x = random.uniform(50, settings.WORLD_WIDTH - 50)
        self.y = random.uniform(50, settings.WORLD_HEIGHT - 50)
        self.memory = Memory()
        self.energy = ENERGY_MAX

        self.state = STATE_CALM
        self.goal_text = INFO_CREATURE_STATE_CALM
        self.panic_active = False
        self.is_talking = False

        self.is_dead = False
        self.death_timer = 0.0
        self.death_cause = None
        self._pending_grief = False
        self.radius = 10

        self.temperament = temperament if temperament in TEMPERAMENT_LIST else random.choice(TEMPERAMENT_LIST)
        self.base_speed_multiplier = SPEED_MULTIPLIER[self.temperament]
        self.curiosity = random.uniform(*CURIOSITY_RANGE.get(self.temperament, (0.3, 0.6)))
        self.curiosity_active = False

        self.social_request_timer = 0.0
        self.share_info_timer = 0.0
        self.social_request_point = None
        self.relationships = {}
        self._helping_target_id = None
        self.helping_commit_timer = 0.0

        self.comfort_point = (self.x, self.y)
        self.known_campfire = None
        self.sleep_spot = None
        self.sleep_spot_campfire = None
        self.target = None
        self.decision_timer = 0.0
        self.speed_factor = 1.0
        self.stuck_check_timer = STUCK_CHECK_INTERVAL
        self.position_at_last_check = (self.x, self.y)
        self.stuck_level = 0
        self.stuck_last_nav_index = 0

        self.seeking_food = False
        self.seeking_water = False
        self.seeking_sanity = False

        self.freeze_timer = 0.0
        self.spike_invuln_timer = 0.0

        self.player_memory = []
        self.knowledge = {"fruit": False, "spike": False, "water": False,
                          "bush": False, "campfire": False}

        self.food_memory_target = None
        self.water_memory_target = None

        # ---------- Глобальная навигация (A* по клеточной карте, creatures/navigation.py) ----------
        self.nav_path = []
        self.nav_path_index = 0
        self.nav_goal = None
        self.nav_recalc_timer = 0.0

        self.wake_threshold = random.uniform(*WAKE_ENERGY_THRESHOLD.get(self.temperament, (85, 90)))
        self.seeking_sleep = False
        self.is_sleeping = False
        self.sleep_forced = False

        self.curiosity_rolled = set()
        self.curiosity_interested = set()

        self.player_relationship = 0.0
        self.calm_timer = 0.0
        self.fear_timer = 0.0
        self.player_fear_timer = 0.0
        self.fear_source = None
        self.is_grabbed = False
        self.grab_before_state = None

        self.age = 0.0
        self.life_stage = LIFE_STAGE_ADULT
        # ---------- Гормональный бум (переходный возраст) ----------
        self.puberty_trigger_age = random.uniform(PUBERTY_TRIGGER_AGE_MIN, PUBERTY_TRIGGER_AGE_MAX)
        self.puberty_done = False
        self.puberty_active = False
        self.puberty_timer = 0.0
        self._puberty_speed_bonus = 0.0
        self._puberty_orig_curiosity = None
        self.puberty_courtship_cooldown = 0.0

        self.child_distress_timer = 0.0
        self.play_target_id = None
        self.play_role = None
        self.play_timer = 0.0
        self.play_cooldown = random.uniform(2.0, 4.0)
        self.known_roads = {}
        self.known_road_links = {}
        self.following_road = None
        self.following_road_active = False
        self.road_progress = 0
        self.road_direction = 1
        self.road_entry_reached = False
        self.road_follow_check_timer = random.uniform(*ROAD_FOLLOW_REROLL_INTERVAL)

        # ---------- Детские дороги ----------
        self.following_child_road = None
        self.child_road_progress = 0
        self.child_road_direction = 1
        self.child_road_entry_reached = False
        self.child_road_play_cooldown = random.uniform(1.0, 3.0)

        # ---------- Детские дороги: скука от повторов ----------
        self.child_road_play_counts = {}
        self.child_road_disinterest = {}

        # ---------- Детские дороги: физическая проверка взрослым ----------
        self.child_road_verify_target_id = None
        self.child_road_verify_progress = 0
        self.child_road_verify_direction = 1
        self.child_road_verify_entry_reached = False
        self.child_road_verify_found_danger = False
        self.child_road_verify_check_timer = random.uniform(*CHILD_ROAD_VERIFY_CHECK_INTERVAL)

        self.partner_id = None
        self.is_pregnant = False
        self.pregnancy_timer = 0.0
        self.parent_ids = None
        self.reuniting_with_partner = False
        self.reunite_commit_timer = 0.0
        self.partner_reunite_cooldown = 0.0
        self.landmark_register_timer = random.uniform(0.0, 1.5)

        # ---------- Устойчивая погоня за территориальным нарушителем ----------
        self.territory_pursuit_target_id = None
        self.territory_pursuit_obj = None
        self.territory_pursuit_last_pos = None
        self.territory_pursuit_commit_timer = 0.0
        # ---------- Опека стариков над случайными детьми ----------
        self.elder_ward_id = None
        self.elder_ward_check_timer = random.uniform(*ELDER_WARD_CHECK_INTERVAL)

        # ---------- Кладбище: перенос трупов ----------
        self.being_carried_by = None  # (для трупов) id несущего
        self.burial_claimant_id = None  # (для трупов) id "хозяина" похорон
        self.burial_target_id = None  # (для живых) id трупа, который несём
        self.graveyard_target_id = None  # (для живых) id кладбища-цели
        self.is_dragging_corpse = False  # True, только пока реально тащит труп (не просто идёт к нему)
        self.known_graveyard = None  # (x, y) - как known_campfire
        self.graveyard_alert_pos = None  # координаты трупа, о котором сообщили старику
        self.graveyard_alert_timer = 0.0

        # ---------- Донашивание еды/воды детям ----------
        self.carried_fruit = False
        self.carried_water = False
        self.feed_target_id = None
        self.parent_feed_check_timer = random.uniform(*PARENT_FEED_CHECK_INTERVAL)
        self.urgent_child_id = None
        self.urgent_child_timer = 0.0

        # ---------- Семейный склад запасов ----------
        self.storage_supply_check_timer = random.uniform(*STORAGE_SUPPLY_CHECK_INTERVAL)
        self.storage_supply_mode = False

        # ---------- Добыча ресурсов и строительство ----------
        self.carry_capacity = random.randint(*CREATURE_CARRY_CAPACITY_RANGE)
        self.carried_resources = {"wood": 0, "stone": 0}
        self.gather_target_id = None
        self.gather_type = None  # "wood" | "stone"
        self.gather_progress = 0.0
        self.construction_target_id = None
        self.construction_phase = None  # None | "deposit" | "build"
        self.gather_needed_amount = None
        self.pending_construction_cleanup = None
        self.construction_check_timer = random.uniform(*CONSTRUCTION_CHECK_INTERVAL)
        self.build_help_check_timer = random.uniform(*BUILD_HELP_CHECK_INTERVAL)

        # ---------- Специализированные подсистемы ----------
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

    # ---------- Геометрия / общие утилиты ----------

    def carried_total(self):
        return self.carried_resources["wood"] + self.carried_resources["stone"]

    def carry_free_space(self):
        return max(0, self.carry_capacity - self.carried_total())

    def can_handle_corpses(self):
        if self.life_stage == LIFE_STAGE_OLD:
            return True
        if (self.life_stage == LIFE_STAGE_ADULT and self.gender == GENDER_MALE
                and self.temperament != TEMPERAMENT_LAZY):
            return True
        return False

    def can_jump_fences(self):
        if self.life_stage != LIFE_STAGE_ADULT:
            return False
        if self.gender == GENDER_FEMALE and self.is_pregnant:
            return False
        return True

    def get_type_name(self):
        return INFO_CREATURE_KIND

    def commit_name_edit(self, new_name):
        _apply_name_edit(self, new_name)

    def on_grab_start(self, world):
        _start_corpse_grab(self, world)

    def on_grab_release(self, game):
        return _handle_corpse_release(self, game)

    def receive_pet(self):
        self.player_reactions.pet()

    def receive_hit(self):
        self.player_reactions.hit()

    def grab_by_player(self):
        self.player_reactions.start_grab()

    def release_by_player(self):
        self.player_reactions.finish_grab()

    # ---------- Жизненный цикл ----------

    def die(self, cause="неизвестно"):
        self.is_dead = True
        self._pending_grief = True
        self.hp = 0
        self.death_timer = CORPSE_LIFETIME
        self.death_cause = cause
        self.target = None
        self.decision_timer = 0.0
        self.panic_active = False
        self.seeking_food = False
        self.seeking_water = False
        self.seeking_sanity = False
        self.freeze_timer = 0.0
        self.spike_invuln_timer = 0.0
        self.calm_timer = 0.0
        self.fear_timer = 0.0
        self.player_fear_timer = 0.0
        self.partner_id = None
        self.is_pregnant = False
        self.pregnancy_timer = 0.0
        self.reuniting_with_partner = False
        self.reunite_commit_timer = 0.0
        self.partner_reunite_cooldown = 0.0
        self.carried_fruit = False
        self.carried_water = False
        self.feed_target_id = None
        self.urgent_child_id = None
        self.fear_source = None
        self.following_road = None
        self.following_road_active = False
        self.road_entry_reached = False
        self.following_child_road = None
        self.child_road_entry_reached = False
        self.child_road_verify_target_id = None
        self.play_target_id = None
        self.play_role = None
        self.is_grabbed = False
        self.grab_before_state = None
        self.social_request_timer = 0.0
        self.social_request_point = None
        self.carried_resources = {"wood": 0, "stone": 0}
        self.gather_target_id = None
        self.gather_type = None
        self.gather_progress = 0.0
        self.construction_target_id = None
        self.construction_phase = None
        self.storage_supply_mode = False
        self.state = STATE_CALM
        self.goal_text = INFO_CREATURE_STATE_DEAD
        self.elder_ward_id = None
        # ---------- Кладбище ----------
        self.burial_target_id = None
        self.graveyard_target_id = None
        self.is_dragging_corpse = False
        self.graveyard_alert_pos = None
        self.graveyard_alert_timer = 0.0
        self.pathfinder.reset_navigation()

    def tick_corpse(self, dt):
        return self.needs.tick_corpse(dt)

    # ---------- Тонкие делегирующие методы (публичный API не меняется) ----------

    def update_needs(self, dt, other_creatures=None, biome_grid=None):
        self.needs.update(dt, other_creatures, biome_grid)
        self.psyche.update(dt)

    def decide(self, ctx):
        return self.brain.decide(ctx)

    def interact(self, fruits, spikes, water_puddles, bushes, campfires, other_creatures,
                storage_fields, dt, walls=None, biome_grid=None):
        self.interactions.process(fruits, spikes, water_puddles, bushes, campfires,
                                   other_creatures, storage_fields, dt, walls=walls,
                                   biome_grid=biome_grid)

    def effective_vision_radius(self):
        return self.aging.effective_vision_radius()

    def can_verify_child_road_safety(self):
        return self.life_stage == LIFE_STAGE_ADULT

    def on_road_deleted(self, road_obj_type, road):
        if road_obj_type == "road":
            if self.following_road is road:
                self.following_road = None
                self.following_road_active = False
                self.road_entry_reached = False
                self.road_progress = 0
            return

        if road_obj_type != "child_road":
            return
        if self.following_child_road is road:
            self.following_child_road = None
            self.child_road_entry_reached = False
            self.child_road_progress = 0
            self.following_road_active = False
        if self.child_road_verify_target_id == road.id:
            self.child_road_verify_target_id = None
            self.child_road_verify_progress = 0
            self.child_road_verify_found_danger = False
            self.child_road_verify_entry_reached = False
            self.following_road_active = False

    def on_road_progress_shift(self, obj_type, road, inserted_index):
        if obj_type == "road":
            if self.following_road is road and self.road_progress >= inserted_index:
                self.road_progress += 1
        elif obj_type == "child_road":
            if self.following_child_road is road and self.child_road_progress >= inserted_index:
                self.child_road_progress += 1

    def on_landmark_removed(self, landmark_type, landmark_id, position):
        if landmark_type == "campfire":
            if self.known_campfire == position:
                self.known_campfire = None
            if self.sleep_spot_campfire == position:
                self.sleep_spot_campfire = None
                self.sleep_spot = None
            self.memory.forget_memory("campfire", position[0], position[1])
        elif landmark_type == "graveyard":
            if self.graveyard_target_id == landmark_id:
                self.graveyard_target_id = None
            if self.known_graveyard == position:
                self.known_graveyard = None
            if self.graveyard_alert_pos == position:
                self.graveyard_alert_pos = None
                self.graveyard_alert_timer = 0.0
            self.memory.forget_memory("graveyard", position[0], position[1])

    # ---------- Отрисовка ----------

    def draw_minimap_color(self):
        if self.gender == GENDER_FEMALE:
            return CREATURE_COLOR_FEMALE_DEAD if self.is_dead else CREATURE_COLOR_FEMALE
        return CREATURE_COLOR_MALE_DEAD if self.is_dead else CREATURE_COLOR_MALE

    def draw(self, screen, screen_pos, show_status_rings=True):
        sx, sy = screen_pos
        if self.gender == GENDER_FEMALE:
            color = CREATURE_COLOR_FEMALE_DEAD if self.is_dead else CREATURE_COLOR_FEMALE
        else:
            color = CREATURE_COLOR_MALE_DEAD if self.is_dead else CREATURE_COLOR_MALE

        # ---------- Радиус круга зависит от стадии жизни ----------
        draw_radius = CHILD_CREATURE_RADIUS if self.life_stage == LIFE_STAGE_CHILD else self.radius

        pygame.draw.circle(screen, color, (int(sx), int(sy)), draw_radius)

        # ---------- Старики: полая белая окружность внутри основного круга ----------
        if self.life_stage == LIFE_STAGE_OLD:
            inner_radius = max(2, draw_radius - 3)
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), inner_radius, 2)

        # ---------- Хват игрока - индикатор взаимодействия, настройка "кольца" на него не влияет ----------
        if self.is_grabbed:
            pygame.draw.circle(screen, (255, 255, 255), (int(sx), int(sy)), draw_radius + 4, 2)
        elif show_status_rings:
            if self.calm_timer > 0:
                pygame.draw.circle(screen, (255, 210, 120), (int(sx), int(sy)), draw_radius + 3, 1)
            elif self.fear_timer > 0:
                pygame.draw.circle(screen, (255, 90, 90), (int(sx), int(sy)), draw_radius + 3, 1)
            elif self.puberty_active:
                pygame.draw.circle(screen, PUBERTY_RING_COLOR, (int(sx), int(sy)), draw_radius + 3, 1)

    # ---------- Сохранение ----------

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
            "comfort_point": list(self.comfort_point),
            "known_campfire": list(self.known_campfire) if self.known_campfire else None,
            "known_graveyard": list(self.known_graveyard) if self.known_graveyard else None,
            "player_memory": self.player_memory,
            "is_dead": self.is_dead,
            "death_timer": self.death_timer,
            "death_cause": self.death_cause,
            "knowledge": self.knowledge,
            "player_relationship": self.player_relationship,
            "known_roads": self.known_roads,
            "known_road_links": self.known_road_links,
            "relationships": self.relationships,
            "gender": self.gender,
            "age": self.age,
            "player_named": self.player_named,
            "partner_id": self.partner_id,
            "is_pregnant": self.is_pregnant,
            "pregnancy_timer": self.pregnancy_timer,
            "parent_ids": list(self.parent_ids) if self.parent_ids else None,
            "carried_fruit": self.carried_fruit,
            "carried_water": self.carried_water,
            "storage_supply_mode": self.storage_supply_mode,
            "elder_ward_id": self.elder_ward_id,
            "burial_target_id": self.burial_target_id,
            "graveyard_target_id": self.graveyard_target_id,
            "feed_target_id": self.feed_target_id,
            "urgent_child_id": self.urgent_child_id,
            "urgent_child_timer": self.urgent_child_timer,
            "puberty_trigger_age": self.puberty_trigger_age,
            "puberty_done": self.puberty_done,
            "puberty_active": self.puberty_active,
            "puberty_timer": self.puberty_timer,
            "puberty_speed_bonus": self._puberty_speed_bonus,
            "puberty_orig_curiosity": self._puberty_orig_curiosity,
            "psyche_joy": self.psyche.joy,
            "psyche_satisfaction": self.psyche.satisfaction,
            "psyche_calmness": self.psyche.calmness,
            "psyche_confidence": self.psyche.confidence,
            "psyche_attachment": self.psyche.attachment,
            "carry_capacity": self.carry_capacity,
            "carried_resources": self.carried_resources,
        }
        with open(os.path.join(folder_path, "state.json"), 'w') as f:
            json.dump(state, f, indent=2)
        self.memory.save(os.path.join(folder_path, "memory.json"))