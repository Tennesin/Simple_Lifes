import time
from . import ci_settings
from . import ci_info
from ...all_needed import geometry
from ...all_needed.weak_owner import WeakOwnerMixin

GRAB_EVAL_MAX_HOLD_TIME = 5.0

_STAT_MAX_MAP = {
    "hp": ci_settings.HP_MAX,
    "hunger": ci_settings.HUNGER_MAX,
    "thirst": ci_settings.THIRST_MAX,
    "consciousness": ci_settings.SANITY_MAX,
    "energy": ci_settings.ENERGY_MAX,
}
_STAT_NEUTRAL_KEYS = ("energy", "consciousness")

class PlayerReactionHandler(WeakOwnerMixin):
    def __init__(self, creature):
        super().__init__(creature)

    def add_memory(self, action, **extra):
        c = self.c
        entry = {"action": action, "timestamp": time.time()}
        entry.update(extra)
        c.player_memory.append(entry)
        if len(c.player_memory) > ci_settings.MAX_PLAYER_MEMORY:
            c.player_memory = c.player_memory[-ci_settings.MAX_PLAYER_MEMORY:]

    def register_touch(self):
        self.add_memory("touch")

    def pet(self):
        c = self.c
        if c.is_dead:
            return
        was_distressed = (c.panic_active or c.fear_timer > 0
                          or c.consciousness < ci_settings.SANITY_LOW_THRESHOLD)
        c.consciousness = min(c.consciousness + ci_settings.PLAYER_PET_SANITY_BONUS, ci_settings.SANITY_MAX)
        c.calm_timer = ci_settings.PLAYER_CALM_DURATION
        c.fear_timer = 0.0
        c.panic_active = False
        c.player_relationship = geometry.clamp(
            c.player_relationship + ci_settings.PLAYER_PET_RELATIONSHIP, -100.0, 100.0)
        c.psyche.on_pet()
        self.add_memory("pet", relationship_after=c.player_relationship)
        c.goal_text = (ci_info.INFO_CREATURE_GOAL_PET_CALM if was_distressed
                       else ci_info.INFO_CREATURE_GOAL_PET_ENJOY)

    def hit(self):
        c = self.c
        if c.is_dead:
            return
        c.hp = max(0, c.hp - ci_settings.PLAYER_HIT_DAMAGE)
        c.calm_timer = 0.0
        c.fear_timer = ci_settings.PLAYER_FEAR_DURATION
        c.player_fear_timer = ci_settings.PLAYER_FEAR_DURATION
        c.fear_source = (c.x, c.y)
        c.following_road = None
        c.following_road_active = False
        c.road_entry_reached = False
        c.following_child_road = None
        c.child_road_progress = 0
        c.child_road_entry_reached = False
        c.player_relationship = geometry.clamp(
            c.player_relationship + ci_settings.PLAYER_HIT_RELATIONSHIP, -100.0, 100.0)
        c.psyche.on_hit()
        self.add_memory("hit", relationship_after=c.player_relationship)
        c.goal_text = ci_info.INFO_CREATURE_GOAL_HIT_FLEE
        if c.hp <= 0:
            c.die(ci_settings.DEATH_CAUSE_PLAYER_HIT)

    def start_grab(self):
        c = self.c
        if c.is_dead:
            return
        c.grab_before_state = {"wellbeing": c.needs.wellbeing_score(), "started_at": time.time()}
        c.is_grabbed = True
        c.target = None
        c.panic_active = False
        c.fear_timer = 0.0
        c.following_road = None
        c.following_road_active = False
        c.road_entry_reached = False
        c.goal_text = ci_info.INFO_CREATURE_GOAL_GRABBED

    def finish_grab(self):
        c = self.c
        c.is_grabbed = False
        if c.grab_before_state is None:
            return
        before = c.grab_before_state["wellbeing"]
        started_at = c.grab_before_state.get("started_at", time.time())
        after = c.needs.wellbeing_score()
        delta = after - before
        hold_duration = time.time() - started_at
        c.grab_before_state = None

        if c.is_dead:
            return

        if hold_duration > GRAB_EVAL_MAX_HOLD_TIME:
            self.add_memory("grab_release", outcome="neutral", relationship_after=c.player_relationship)
            c.goal_text = ci_info.INFO_CREATURE_GOAL_GRAB_NEUTRAL
            return

        if delta > 0.03:
            c.player_relationship = geometry.clamp(
                c.player_relationship + ci_settings.PLAYER_GRAB_GOOD_RELATIONSHIP, -100.0, 100.0)
            c.psyche.on_grab_release("better")
            self.add_memory("grab_release", outcome="better", relationship_after=c.player_relationship)
            c.calm_timer = max(c.calm_timer, ci_settings.PLAYER_CALM_DURATION * 0.5)
            c.goal_text = ci_info.INFO_CREATURE_GOAL_GRAB_GOOD
        elif delta < -0.03:
            c.player_relationship = geometry.clamp(
                c.player_relationship + ci_settings.PLAYER_GRAB_BAD_RELATIONSHIP, -100.0, 100.0)
            c.psyche.on_grab_release("worse")
            self.add_memory("grab_release", outcome="worse", relationship_after=c.player_relationship)
            c.fear_timer = max(c.fear_timer, ci_settings.PLAYER_FEAR_DURATION * 0.6)
            c.player_fear_timer = max(c.player_fear_timer, ci_settings.PLAYER_FEAR_DURATION * 0.6)
            c.fear_source = (c.x, c.y)
            c.goal_text = ci_info.INFO_CREATURE_GOAL_GRAB_BAD
        else:
            self.add_memory("grab_release", outcome="neutral", relationship_after=c.player_relationship)
            c.goal_text = ci_info.INFO_CREATURE_GOAL_GRAB_NEUTRAL

    def mark_favorite(self):
        c = self.c
        if c.is_dead or c.favorite_bonus_applied:
            return
        c.favorite_bonus_applied = True
        c.player_relationship = geometry.clamp(
            c.player_relationship + ci_settings.FAVORITE_ASSIGN_RELATIONSHIP_BONUS, -100.0, 100.0)
        self.add_memory("marked_favorite", relationship_after=c.player_relationship)

    def adjust_stat(self, stat_key, direction):
        c = self.c
        if c.is_dead:
            return
        max_value = _STAT_MAX_MAP.get(stat_key)
        if max_value is None:
            return

        current = getattr(c, stat_key)
        delta = direction * max_value * ci_settings.STAT_ADJUST_STEP_FACTOR
        new_value = max(0, min(current + delta, max_value))
        setattr(c, stat_key, new_value)

        if stat_key == "hp" and new_value <= 0:
            c.die(ci_settings.DEATH_CAUSE_PLAYER_HIT)
            return

        if stat_key in _STAT_NEUTRAL_KEYS:
            return

        if new_value > current:
            c.player_relationship = geometry.clamp(
                c.player_relationship + ci_settings.STAT_ADJUST_RELATIONSHIP_GOOD, -100.0, 100.0)
            self.add_memory("stat_adjust", stat=stat_key, outcome="better",
                            relationship_after=c.player_relationship)
        elif new_value < current:
            c.player_relationship = geometry.clamp(
                c.player_relationship + ci_settings.STAT_ADJUST_RELATIONSHIP_BAD, -100.0, 100.0)
            self.add_memory("stat_adjust", stat=stat_key, outcome="worse",
                            relationship_after=c.player_relationship)