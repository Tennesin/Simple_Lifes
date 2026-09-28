"""Данные плана миграции Creature для scan_creature_refs.py. Обновлять здесь -
код сканера при этом трогать не нужно."""

ACTIVE_STAGE = 14   # обновляй по мере продвижения

PLAN_STAGES = {
    0: (
        # Шаг 0 - подготовка state/, StateBlock. Полей нет. РЕАЛИЗОВАНО.
    ),
    1: (
        # Шаг 1 - домен "Пубертат" (PubertyState). РЕАЛИЗОВАНО.
        "puberty_trigger_age",
        "puberty_done",
        "puberty_active",
        "puberty_timer",
        "_puberty_speed_bonus",
        "_puberty_orig_curiosity",
        "puberty_courtship_cooldown",
        "puberty_courtship_target_id",
        "puberty_courtship_timer",
        "puberty_courtship_deadline",
        "puberty_courtship_fail_streak",
        "puberty_courtship_avoid",
    ),
    2: (
        # Шаг 2 - домен "Труп/кладбище" (BurialState). РЕАЛИЗОВАНО.
        "being_carried_by",
        "burial_claimant_id",
        "burial_target_id",
        "graveyard_target_id",
        "is_dragging_corpse",
        "known_graveyard",
        "known_graveyard_id",
        "graveyard_alert_pos",
        "graveyard_alert_timer",
    ),
    3: (
        # Шаг 3 - домен "Территория" (внутри уже существующего
        # CreatureTerritory в life_cycle.py). РЕАЛИЗОВАНО.
        "territory_pursuit_target_id",
        "territory_pursuit_obj",
        "territory_pursuit_last_pos",
        "territory_pursuit_commit_timer",
    ),
    4: (
        # Шаг 4 - домен "Детские дороги": следование (ChildRoadPlayState,
        # владелец - child_ai.py:_ChildRoadPlayMixin) + физическая проверка
        # взрослым (RoadVerifyState, владелец - patterns/roads.py:ChildRoadVerification).
        # Один общий скан, но на выходе - ДВА отдельных StateBlock.

        # --- следование (игра) ---
        "following_child_road",
        "child_road_progress",
        "child_road_direction",
        "child_road_entry_reached",
        "child_road_play_cooldown",
        "child_road_play_counts",
        "child_road_disinterest",

        # --- проверка безопасности взрослым ---
        "child_road_verify_target_id",
        "child_road_verify_progress",
        "child_road_verify_direction",
        "child_road_verify_entry_reached",
        "child_road_verify_found_danger",
        "child_road_verify_check_timer",
    ),
    5: (
        # Шаг 5 - Стройка/добыча ресурсов + Кормление (сознательно вместе -
        # делать после появления реестра типов зданий, см. план).
        "carry_capacity",
        "carried_resources",
        "gather_target_id",
        "gather_type",
        "gather_progress",
        "gather_needed_amount",
        "construction_target_id",
        "construction_phase",
        "pending_construction_cleanup",
        "pending_site_cleanup",
        "construction_check_timer",
        "build_help_check_timer",
        "carried_fruit",
        "carried_water",
        "feed_target_id",
        "parent_feed_check_timer",
        "urgent_child_id",
        "urgent_child_timer",
    ),
    6: (
        # Шаг 6 - Семейный склад запасов ("Склад/дом" - снабжение).
        "storage_supply_check_timer",
        "storage_supply_mode",
    ),
    7: (
        # Шаг 7 - Жильё.
        "home_id",
        "home_eviction_timer",
        "at_home",
    ),
    8: (
        # Шаг 8 - Семья/размножение.
        "partner_id",
        "is_pregnant",
        "pregnancy_timer",
        "parent_ids",
        "reuniting_with_partner",
        "reunite_commit_timer",
        "partner_reunite_cooldown",
    ),
    9: (
        # Шаг 9 - Опека стариков над чужими детьми.
        "elder_ward_id",
        "elder_ward_check_timer",
    ),
    10: (
        # Шаг 10 - Дороги игрока (не детские; следование по нарисованной дороге).
        "known_roads",
        "known_road_links",
        "following_road",
        "following_road_active",
        "road_progress",
        "road_direction",
        "road_entry_reached",
        "road_follow_check_timer",
    ),
    11: (
        # Шаг 11 - Ориентиры (костёр/сон/точка комфорта).
        "comfort_point",
        "known_campfire",
        "known_campfire_id",
        "sleep_spot",
        "sleep_spot_campfire",
        "landmark_register_timer",
    ),
    12: (
        # Шаг 12 - Навигация / ИИ-троттлинг.
        "target",
        "decision_timer",
        "ai_dt_debt",
        "ai_last_goal",
        "ai_plan_valid",
        "speed_factor",
        "stuck_check_timer",
        "position_at_last_check",
        "stuck_level",
        "stuck_last_nav_index",
        "nav_path",
        "nav_path_index",
        "nav_goal",
        "nav_recalc_timer",
        "nav_search_failed",
    ),
    13: (
        "seeking_food", "seeking_water", "seeking_sanity", "seeking_sleep",
        "wake_threshold", "is_sleeping", "sleep_forced", "freeze_timer",
        "spike_invuln_timer",
    ),
    14: (
        "player_memory", "knowledge", "food_memory_target", "water_memory_target",
    ),
    15: (
        # Шаг 15 - Реакции игрок<->существо.
        "player_relationship",
        "calm_timer",
        "fear_timer",
        "player_fear_timer",
        "fear_source",
        "favorite_bonus_applied",
        "is_grabbed",
        "grab_before_state",
    ),
    16: (
        # Шаг 16 - Возраст / стадия жизни (без puberty - тот уже отдельно).
        "age",
        "life_stage",
    ),
    17: (
        # Шаг 17 - Поведение ребёнка (испуг, догонялки).
        "child_distress_timer",
        "play_target_id",
        "play_role",
        "play_timer",
        "play_cooldown",
    ),
    18: (
        # Шаг 18 - Социальное (отношения, запросы компании, эмпатия).
        "relationships",
        "social_request_timer",
        "social_request_point",
        "share_info_timer",
        "_helping_target_id",
        "helping_commit_timer",
    ),
    19: (
        # Шаг 19 - Характер / скорость / любопытство.
        "temperament",
        "base_speed_multiplier",
        "curiosity",
        "curiosity_active",
        "curiosity_rolled",
        "curiosity_interested",
    ),
    20: (
        # Шаг 20 - Смерть.
        "is_dead",
        "death_timer",
        "death_cause",
        "_pending_grief",
    ),
    21: (
        # Шаг 21 - Текущее состояние / отображаемая цель.
        "state",
        "goal_text",
        "panic_active",
        "is_talking",
    ),
    22: (
        # Шаг 22 (ПОСЛЕДНИЙ, самый рискованный) - Витальность.
        "hp",
        "hunger",
        "thirst",
        "consciousness",
        "sanity_decay_timer",
        "energy",
    ),
    # Идентичность (id, gender, name, player_named, x, y, radius) сознательно
    # НЕ вынесена отдельным этапом: это не поведенческое состояние, а
    # перманентные идентификаторы/геометрия - план не предполагает её миграцию.
}

# Поля, которые сознательно не мигрируют (контракт CreatureBase / all_needed / общая шина ИИ)
NEVER_MIGRATE = {
    "nav_path", "nav_path_index", "nav_goal", "nav_recalc_timer", "nav_search_failed",
    "speed_factor", "spike_invuln_timer",
    "is_dead", "hp", "hunger", "thirst", "energy",
    "target", "decision_timer", "state", "goal_text", "panic_active",
    "age", "life_stage", "temperament",
    "consciousness", "sanity_decay_timer",
}