"""Текстовые константы, специфичные для расы 'Круг': состояния, цели ИИ,
подписи панели существа, психика, взаимоотношения, гендерные варианты фраз."""

from .ci_settings import (
    GENDER_FEMALE, TEMPERAMENT_NORMAL, TEMPERAMENT_EXPLORER, TEMPERAMENT_LAZY,
    LIFE_STAGE_ADULT, LIFE_STAGE_OLD, STATE_SEEKING,
)

# --------------------- Названия объектов ---------------------
INFO_OBJECT_STORAGE_FIELD = "Склад"
INFO_OBJECT_GRAVEYARD = "Кладбище"
INFO_OBJECT_CHILD_ROAD = "Детская дорога"
INFO_OBJECT_CONSTRUCTION_SITE = "Стройплощадка"

# --------------------- Кладбище ---------------------
INFO_BTN_GRAVEYARD = "Кладбище"
INFO_GRAVEYARD_DEFAULT_NAME = "Кладбище"
INFO_GRAVEYARD_ID = "ID: {graveyard_id}"
INFO_GRAVEYARD_ARCHIVE_EMPTY = "Здесь пока никого не хоронили"
INFO_GRAVEYARD_ARCHIVE_ENTRY = "{name} [{id}]"
INFO_GRAVEYARD_DETAILS_BTN = "Подробности"
INFO_GRAVEYARD_DETAILS_TITLE = "Сведения о похороненном"
INFO_GRAVEYARD_DETAILS_NAME = "Имя: {name}"
INFO_GRAVEYARD_DETAILS_ID = "ID: {id}"
INFO_GRAVEYARD_DETAILS_GENDER = "Пол: {gender}"
INFO_GRAVEYARD_DETAILS_TEMPERAMENT = "Характер: {temperament}"
INFO_GRAVEYARD_DETAILS_AGE = "Возраст на момент смерти: {age} мин."
INFO_GRAVEYARD_DETAILS_CAUSE = "Причина смерти: {cause}"
INFO_GRAVEYARD_DETAILS_TIME_LEFT = "Подробности исчезнут через: {time}"
INFO_GRAVEYARD_DETAILS_CLOSE = "Закрыть"
INFO_BTN_GENEALOGY = "Геном"
INFO_GENEALOGY_TITLE = "Древо Родословной: {name}"
INFO_GENEALOGY_CLOSE = "Закрыть"
INFO_GENEALOGY_UNKNOWN = "?"

# --------------------- Тип существа ---------------------
INFO_CREATURE_KIND = "Круг"

INFO_INFO_GENDER = "Пол: {gender}"
INFO_GENDER_MALE = "Самец"
INFO_GENDER_FEMALE = "Самка"

# --------------------- Состояния и цели существ ---------------------
INFO_CREATURE_STATE_CALM = "Осматривается"
INFO_CREATURE_STATE_DEAD = "Мёртв"

INFO_CREATURE_GOAL_PET_CALM = "Успокаивается от поглаживания"
INFO_CREATURE_GOAL_PET_ENJOY = "Наслаждается поглаживанием"
INFO_CREATURE_GOAL_HIT_FLEE = "Напуган и пытается отпрянуть"
INFO_CREATURE_GOAL_GRABBED = "Схвачен игроком"
INFO_CREATURE_GOAL_GRAB_GOOD = "Похоже, тут ему понравилось"
INFO_CREATURE_GOAL_GRAB_BAD = "Не понравилось, куда его перенесли"
INFO_CREATURE_GOAL_GRAB_NEUTRAL = "Немного растерян после перемещения"
INFO_CREATURE_GOAL_NAMED = "Получил имя от игрока"
INFO_CREATURE_GOAL_FROZEN = "Замер на месте"
INFO_CREATURE_GOAL_LAZY_REST = "Отдыхает у зоны комфорта"
INFO_CREATURE_GOAL_EXPLORE = "Исследует местность"
INFO_CREATURE_GOAL_SEEK_SAFETY = "Ищет безопасное место"
INFO_CREATURE_GOAL_SEEK_FOOD = "Направляется к еде"
INFO_CREATURE_GOAL_SEEK_FOOD_ACTIVE = "Активно ищет еду"
INFO_CREATURE_GOAL_SEEK_WATER = "Направляется к воде"
INFO_CREATURE_GOAL_SEEK_WATER_ACTIVE = "Активно ищет воду"
INFO_CREATURE_GOAL_SANITY_URGENT_FIRE = "Спешит к знакомому костру"
INFO_CREATURE_GOAL_SANITY_FIRE = "Тянется к знакомому костру"
INFO_CREATURE_GOAL_SANITY_URGENT_COMPANION_FIRE = "Спешит к сородичу у костра"
INFO_CREATURE_GOAL_SANITY_COMPANION_FIRE = "Подходит к сородичу у костра"
INFO_CREATURE_GOAL_SANITY_TALK = "Греется у костра и беседует"
INFO_CREATURE_GOAL_SANITY_ALONE = "Греется у костра в одиночестве"
INFO_CREATURE_GOAL_SANITY_URGENT_ANYONE = "Отчаянно ищет хоть кого-то рядом"
INFO_CREATURE_GOAL_SANITY_COMPANIONS = "Тянется к сородичам"
INFO_CREATURE_GOAL_SANITY_URGENT_NO_FIRE = "Мечется в поисках хоть какого-то утешения"
INFO_CREATURE_GOAL_SANITY_NO_FIRE = "Смутно тоскует по теплу и общению"
INFO_CREATURE_GOAL_SOCIAL_RESPOND_GO = "Идёт составить компанию сородичу"
INFO_CREATURE_GOAL_SOCIAL_RESPOND_TALK = "Остаётся рядом, поддерживая компанию"
INFO_CREATURE_GOAL_TERRITORY_GUARD = "Прогоняет чужака со своей территории"
INFO_CREATURE_GOAL_SLEEP_GO_FIRE = "Идёт к костру, чтобы поспать"
INFO_CREATURE_GOAL_SLEEP_AT_FIRE = "Устраивается спать у костра"
INFO_CREATURE_GOAL_SLEEP_INTUITIVE = "Смутно ищет тёплое место для сна"
INFO_CREATURE_GOAL_SLEEP_ON_MOVE = "Борется со сном на ходу"
INFO_CREATURE_GOAL_HELP_APPROACH = "Спешит на помощь сородичу"
INFO_CREATURE_GOAL_HELP_LEAD = "Ведёт сородича к костру"
INFO_CREATURE_GOAL_HELP_TALK = "Поддерживает сородича разговором"
INFO_CREATURE_GOAL_FAMILY_REUNITE = "Возвращается к партнёру"
INFO_CREATURE_GOAL_CHILD_DISTRESS = "Испуган и ищет знакомый костёр"
INFO_CREATURE_GOAL_CHILD_PLAY_TAG = "Играет в догонялки"
INFO_CREATURE_GOAL_CHILD_PLAY_ROAD = "Бегает по дороге просто так"
INFO_CREATURE_GOAL_CHILD_EXPLORE = "Неуверенно осматривается рядом"
INFO_CREATURE_GOAL_CHILD_HUNGER_SIGNAL = "Ищет костёр и зовёт родителей на помощь"
INFO_CREATURE_GOAL_CHILD_ROAD_APPROACH = "Бежит к детской дороге"
INFO_CREATURE_GOAL_CHILD_ROAD_PLAY = "С восторгом бегает по детской дороге"
INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY = "Идёт проверять детскую дорогу"
INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY_SAFE = "Прошёл детскую дорогу — она безопасна"
INFO_CREATURE_GOAL_CHILD_ROAD_VERIFY_DANGER = "Прошёл детскую дорогу — обнаружил опасность"
INFO_CREATURE_GOAL_CHILD_ROAD_DANGER = "Дорога оказалась опасной! Убегает"
INFO_CREATURE_GOAL_ELDER_WARD_APPROACH = "Спешит к беспризорному ребёнку"
INFO_CREATURE_GOAL_ELDER_WARD_FETCH = "Идёт добыть еду или воду для чужого ребёнка"
INFO_CREATURE_GOAL_ELDER_WARD_LEAD = "Ведёт чужого ребёнка к костру"
INFO_CREATURE_GOAL_ELDER_WARD_COMFORT = "Присматривает за чужим ребёнком"
INFO_CREATURE_GOAL_ELDER_HAZARD_KNOWN = "Узнал знакомую опасность с первого взгляда"
INFO_CREATURE_GOAL_FEED_FETCH_FOOD = "Идёт за фруктом для ребёнка"
INFO_CREATURE_GOAL_FEED_CARRY_FOOD = "Подбирает фрукт, чтобы отнести ребёнку"
INFO_CREATURE_GOAL_FEED_FETCH_WATER = "Идёт за водой для ребёнка"
INFO_CREATURE_GOAL_FEED_CARRY_WATER = "Набирает воду, чтобы отнести ребёнку"
INFO_CREATURE_GOAL_FEED_DELIVER = "Несёт еду/воду голодному ребёнку"
INFO_CREATURE_GOAL_FEED_DONE = "Покормил ребёнка"
INFO_CREATURE_GOAL_STORAGE_DELIVER = "Несёт запасы на склад"
INFO_CREATURE_GOAL_STORAGE_STOCKED = "Пополнил семейный склад"
INFO_CREATURE_GOAL_CHILD_SEEK_STORAGE = "Идёт к семейным запасам за едой"
INFO_CREATURE_GOAL_CURIOSITY_HAZARD_KNOWN = "Разглядел и запомнил: это опасно"
INFO_CREATURE_GOAL_CURIOSITY_HAZARD_STUDY = "Настороженно разглядывает нечто незнакомое"
INFO_CREATURE_GOAL_CURIOSITY_UNKNOWN = "Заинтересовался неизвестным объектом"
INFO_CREATURE_GOAL_PUBERTY_COURT = "Настойчиво ищет пару, повинуясь гормонам"
INFO_CREATURE_GOAL_ROAD_FOLLOW = "Идёт по нарисованной дороге, не сворачивая"
INFO_CREATURE_GOAL_ROAD_APPROACH = "Направляется к нарисованной дороге"
INFO_CREATURE_GOAL_ROAD_KNOWN_ROUTE = "Уверенно идёт знакомой дорогой к цели"
INFO_CREATURE_GOAL_ROAD_CROSSING_KNOWN = "Сворачивает на перекрёстке к знакомой цели"
INFO_CREATURE_GOAL_ROAD_CROSSING_SWITCH = "Из любопытства сворачивает на другую дорогу"
INFO_CREATURE_GOAL_ROAD_USEFUL = "Дорога привела к чему-то полезному"
INFO_CREATURE_GOAL_ROAD_USELESS_DANGER = "Дорога оказалась опасной и бесполезной"
INFO_CREATURE_GOAL_ROAD_EMPTY = "Дорога привела в пустоту"
INFO_CREATURE_GOAL_ROAD_USEFUL_SIMPLE = "Дорога оказалась полезной"
INFO_CREATURE_GOAL_ROAD_DEADLY = "Дорога оказалась смертельно опасной — прочь отсюда"
INFO_CREATURE_GOAL_SLEEP_FORCED = "Без сил, спит прямо тут"
INFO_CREATURE_GOAL_SLEEP_FIRE = "Спит у костра"
INFO_CREATURE_GOAL_PANIC_FLEE = "В ужасе убегает подальше от того места"
INFO_CREATURE_GOAL_URGENT_FOOD = "Ищет еду, чтобы выжить"
INFO_CREATURE_GOAL_GATHER_WOOD = "Идёт добывать древесину"
INFO_CREATURE_GOAL_GATHER_STONE = "Идёт добывать камень"
INFO_CREATURE_GOAL_GATHERING_WOOD = "Рубит дерево"
INFO_CREATURE_GOAL_GATHERING_STONE = "Добывает камень"
INFO_CREATURE_GOAL_CONSTRUCTION_GO = "Несёт материалы на стройку"
INFO_CREATURE_GOAL_CONSTRUCTION_DEPOSIT = "Складывает материалы на стройплощадке"
INFO_CREATURE_GOAL_CONSTRUCTION_BUILD = "Строит объект"
INFO_CREATURE_GOAL_CONSTRUCTION_HELP = "Спешит помочь со стройкой"
INFO_CREATURE_GOAL_CONSTRUCTION_DONE = "Завершил постройку"

INFO_CREATURE_GOAL_CORPSE_FLEE_FIRE = "Бежит от тела к костру, зовя на помощь"
INFO_CREATURE_GOAL_CORPSE_FLEE_BLIND = "В ужасе убегает от тела"
INFO_CREATURE_GOAL_CORPSE_APPROACH = "Осторожно подходит к телу сородича"
INFO_CREATURE_GOAL_CORPSE_CARRY = "Медленно несёт тело к кладбищу"
INFO_CREATURE_GOAL_CORPSE_ALERT = "Спешит проверить весть о теле"

# --------------------- Психика (панель существа) ---------------------
INFO_PSYCHE_TOGGLE = "Психика"
INFO_PSYCHE_TITLE = "Психика"
INFO_PSYCHE_PLAYER_REL = "К игроку"
INFO_PSYCHE_CONSCIOUSNESS = "Сознание"
INFO_PSYCHE_JOY_TITLE = "Радость"
INFO_PSYCHE_JOY_LEFT = "Грусть"
INFO_PSYCHE_JOY_RIGHT = "Счастье"
INFO_PSYCHE_SATISFACTION_TITLE = "Удовлетворённость"
INFO_PSYCHE_SATISFACTION_LEFT = "Разочарование"
INFO_PSYCHE_SATISFACTION_RIGHT = "Довольство"
INFO_PSYCHE_CALM_TITLE = "Тревожность"
INFO_PSYCHE_CALM_LEFT = "Тревога"
INFO_PSYCHE_CALM_RIGHT = "Спокойствие"
INFO_PSYCHE_CONFIDENCE_TITLE = "Уверенность"
INFO_PSYCHE_CONFIDENCE_LEFT = "Неуверенность"
INFO_PSYCHE_CONFIDENCE_RIGHT = "Уверенность"
INFO_PSYCHE_ATTACHMENT_TITLE = "Привязанность"
INFO_PSYCHE_ATTACHMENT_LEFT = "Отчуждённость"
INFO_PSYCHE_ATTACHMENT_RIGHT = "Привязанность"

# --------------------- Панель информации о существе ---------------------
INFO_INFO_ID = "ID: {creature_id}"
INFO_INFO_NO_NAME = "без имени, клик — задать"
INFO_INFO_KIND = "Вид: {kind}"
INFO_INFO_AGE_MINUTES = "Возраст: {age}"
INFO_INFO_FATHER = "Папа: {name}"
INFO_INFO_MOTHER = "Мама: {name}"
INFO_INFO_HEAVEN = "Небеса"
INFO_INFO_UNKNOWN_PARENT = "Неизвестно"
INFO_INFO_SONS = "Сыновья: {names}"
INFO_INFO_DAUGHTERS = "Дочери: {names}"
INFO_INFO_PARTNER = "Партнёр: {name}"
INFO_INFO_PARTNER_NONE = "нет"
INFO_INFO_CHILDREN = "Дети: {names}"
INFO_INFO_CHILDREN_NONE = "нет"
INFO_INFO_PREGNANT = "Беременна"
INFO_INFO_PUBERTY_ACTIVE = "Гормональный всплеск"
INFO_INFO_STATUS_DEAD = "Статус: труп"
INFO_INFO_DEATH_TIMER = "Исчезнет через: {time:.1f} с"
INFO_INFO_TEMPERAMENT = "Характер: {temperament}"
INFO_INFO_HP = "Здоровье"
INFO_INFO_HUNGER = "Голод"
INFO_INFO_THIRST = "Жажда"
INFO_INFO_ENERGY = "Энергия"
INFO_INFO_STATE = "Состояние: {state}"
INFO_INFO_GOAL = "Цель: {goal}"
INFO_INFO_RELATIONSHIP = "К игроку: {label}"

# --------------------- Отношения существа к игроку / другим ---------------------
INFO_RELATIONSHIP_DESPISE = "Презирает"
INFO_RELATIONSHIP_AFRAID = "Опасается"
INFO_RELATIONSHIP_WARY = "Настороженно"
INFO_RELATIONSHIP_NEUTRAL = "Нейтрален"
INFO_RELATIONSHIP_FRIENDLY = "Доброжелателен"
INFO_RELATIONSHIP_TRUST = "Доверяет"
INFO_RELATIONSHIP_DEVOTED = "Предан"
INFO_RELATIONSHIP_FEAR = "Острый страх"
INFO_RELATIONSHIP_CALMED = "Успокоен"
INFO_RELATIONSHIPS_TITLE = "Взаимоотношения"
INFO_RELATIONSHIPS_MALES = "Самцы"
INFO_RELATIONSHIPS_FEMALES = "Самки"
INFO_RELATIONSHIPS_EMPTY = "Нет прямых контактов"

# --------------------- Направления для интуитивной памяти ---------------------
INFO_COMPASS_DIRECTIONS = [
    "восток", "северо-восток", "север", "северо-запад",
    "запад", "юго-запад", "юг", "юго-восток",
]
INFO_DISTANCE_BUCKET_NEAR = "рядом"
INFO_DISTANCE_BUCKET_MEDIUM = "на среднем расстоянии"
INFO_DISTANCE_BUCKET_FAR = "далеко"

# --------------------- Утилиты ---------------------
INFO_TOOL_CHILD_ROAD_HINT = "Зажмите и ведите ЛКМ — рисовать детскую дорогу"
INFO_SETTINGS_MINIMAP_CONSTRUCTIONS = "Показать сооружения на мини-карте"

# --------------------- Женские варианты фраз ---------------------
INFO_FEMALE_VARIANTS = {
    STATE_SEEKING: "Занята",
    INFO_CREATURE_STATE_DEAD: "Мертва",

    INFO_CREATURE_GOAL_HIT_FLEE: "Напугана и пытается отпрянуть",
    INFO_CREATURE_GOAL_GRABBED: "Схвачена игроком",
    INFO_CREATURE_GOAL_GRAB_GOOD: "Похоже, тут ей понравилось",
    INFO_CREATURE_GOAL_GRAB_BAD: "Не понравилось, куда её перенесли",
    INFO_CREATURE_GOAL_GRAB_NEUTRAL: "Немного растеряна после перемещения",
    INFO_CREATURE_GOAL_NAMED: "Получила имя от игрока",
    INFO_CREATURE_GOAL_FROZEN: "Замерла на месте",
    INFO_CREATURE_GOAL_CHILD_DISTRESS: "Испугана и ищет знакомый костёр",
    INFO_CREATURE_GOAL_CURIOSITY_HAZARD_KNOWN: "Разглядела и запомнила: это опасно",
    INFO_CREATURE_GOAL_CURIOSITY_UNKNOWN: "Заинтересовалась неизвестным объектом",
    INFO_CREATURE_GOAL_FEED_DONE: "Покормила ребёнка",
    INFO_CREATURE_GOAL_STORAGE_STOCKED: "Пополнила семейный склад",
    INFO_CREATURE_GOAL_ELDER_HAZARD_KNOWN: "Узнала знакомую опасность с первого взгляда",

    INFO_RELATIONSHIP_NEUTRAL: "Нейтральна",
    INFO_RELATIONSHIP_FRIENDLY: "Доброжелательна",
    INFO_RELATIONSHIP_DEVOTED: "Предана",
    INFO_RELATIONSHIP_CALMED: "Успокоена",

    TEMPERAMENT_NORMAL: "Обычная",
    TEMPERAMENT_EXPLORER: "Исследовательница",
    TEMPERAMENT_LAZY: "Лентяйка",

    LIFE_STAGE_ADULT: "Взрослая",
    LIFE_STAGE_OLD: "Старуха",
}

# --------------------- Объекты и механики, специфичные для расы 'Круг' ---------------------
INFO_BTN_DRAW_CHILD_ROAD = "Детская дорога"
INFO_BTN_CREATE_MALE = "Самец"
INFO_BTN_CREATE_FEMALE = "Самка"

INFO_INFO_CLAIMED_BY = "Территория самца: {name}"
INFO_INFO_STORAGE_FRUITS = "Фруктов на складе: {count}"
INFO_INFO_STORAGE_WATER = "Воды на складе: {count}"
INFO_INFO_STORAGE_OWNER = "Владелец: {name}"
INFO_INFO_STORAGE_OWNER_PUBLIC = "Владелец: общий склад"
INFO_INFO_CONSTRUCTION_WOOD = "Древесина: {deposited}/{required}"
INFO_INFO_CONSTRUCTION_STONE = "Камень: {deposited}/{required}"
INFO_INFO_CONSTRUCTION_PROGRESS = "Стройка: {percent}%"

INFO_INFO_DEATH_CAUSE_STARVATION = "Причина: голод/жажда/раны"
INFO_INFO_DEATH_CAUSE_SANITY = "Причина: не выдержал одиночества"
INFO_INFO_DEATH_CAUSE_OLD_AGE = "Причина: старость"
INFO_INFO_DEATH_CAUSE_PLAYER_HIT = "Причина: погиб от руки игрока"
INFO_INFO_DEATH_CAUSE_DROWNING = "Причина: утонул в море"

DEATH_CAUSE_DISPLAY_MAP = {
    "истощение": INFO_INFO_DEATH_CAUSE_STARVATION,
    "помутнение сознания": INFO_INFO_DEATH_CAUSE_SANITY,
    "старость": INFO_INFO_DEATH_CAUSE_OLD_AGE,
    "получил травму от игрока": INFO_INFO_DEATH_CAUSE_PLAYER_HIT,
    "утонул в море": INFO_INFO_DEATH_CAUSE_DROWNING,
}

def gendered_text(text, gender):
    if gender == GENDER_FEMALE:
        return INFO_FEMALE_VARIANTS.get(text, text)
    return text