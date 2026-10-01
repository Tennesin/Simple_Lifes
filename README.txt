=========================================================================
ИНСТРУКЦИЯ ДЛЯ ИИ, РАБОТАЮЩЕГО НАД ПРОЕКТОМ Simple_Lifes
=========================================================================

Этот файл - не описание игры, а свод архитектурных правил и конвенций
проекта. Перед любой правкой кода прочитай его целиком. Структуру файлов
и папок смотри в "СКЕЛЕТ_ПРОДВИНУТЫЙ.txt" - он создаётся скриптом
text_maker.py и является источником истины по составу проекта.

О самой игре: Simple_Lifes - симулятор жизни, а не стратегия. Игрок не
отдаёт приказов существам - они сами решают, куда идти, что есть, с кем
дружить и что строить. Роль игрока - роль обстоятельств: создать мир,
изменить ландшафт, подкинуть ресурс, нарисовать дорогу и понаблюдать.

Разделы 1-9 и 12 - фундамент: менять их можно только по прямой просьбе
автора. Разделы 10, 11 и 13 - практические соглашения.

-------------------------------------------------------------------
1. ГРАНИЦА МЕЖДУ ЯДРОМ, РАСАМИ И ЖИВОТНЫМИ (правило №1)
-------------------------------------------------------------------

- Ядро (game/, ui/, objects.py, settings.py, info.py, renderer.py,
  biome.py, player.py и т.п.) не должно знать ничего о конкретных расах
  и видах животных.
- За чтение и интеграцию рас/животных отвечают ИСКЛЮЧИТЕЛЬНО
  game/race_registry.py и game/animal_registry.py.
- Никакой файл, кроме этих двух реестров, не импортирует что-либо из
  "creatures/races/*" и "creatures/animals/*" напрямую.
- Ядру разрешены импорты из "creatures/all_needed/" - это общий,
  расо-независимый инструментарий (геометрия, память, AI-утилиты,
  навигация, диета, базовые классы).
- Направление зависимостей: all_needed <- ядро (game/ui/objects) <-
  реестры <- races/animals. Код рас и животных вправе импортировать
  ядро; обратное запрещено.
- Если ядру "срочно нужно" узнать что-то о расе (например, заимпортировать
  Creature в object_manager) - это ошибка. Правильный путь: добавить
  поле/callback в дескриптор и прочитать его через *_registry.py.
- Известные исключения (исторический долг, в новый код НЕ копировать):
    memory.py: методы campfire/graveyard;
    objects.py: claimed_by у Bush и WaterPuddle;
    world_manager: sync_claims_count(territory), подсчёт campfires в
      _load_entry_counts;
    simulation: _cleanup_exhausted_water (territory), _cleanup_transient_
      objects (build_type/construction_sites);
    ui/object_panel: проверка build_type;
    renderer._draw_creatures: housing.at_home (вместо is_hidden());
    animals: GrazerAI читает world.wolves, WolfAI читает cows/sheep.
  Выносить их в дескрипторы - только по просьбе автора.
- Файлы "creatures/races/<раса>/mechanics/" - переходный слой: тут можно
  одновременно использовать Creature расы и понятия ядра (Camera,
  WorldState, game.*). В корень папки расы такой код класть нельзя, в
  ядро - тоже.
- Код расы/животного импортирует ядро только через game.race_registry,
  game.animal_registry, game.widgets, objects, settings, info. Импорт
  game.game, game.world_manager, game.world_context на уровне модуля
  даёт циклический импорт: эти модули вызывают all_races()/all_animals()
  при импорте.

-------------------------------------------------------------------
2. РЕГИСТРАЦИЯ РАСЫ / ЖИВОТНОГО ЧЕРЕЗ ДЕСКРИПТОРЫ
-------------------------------------------------------------------

- Раса: RACE_DESCRIPTOR (RaceDescriptor) в creatures/races/<раса>/race.py.
  Животное: ANIMAL_DESCRIPTOR (AnimalDescriptor) в
  creatures/animals/<вид>/animal.py. Обнаружение автоматическое
  (pkgutil.iter_modules), реестры ленивые и кешируются.
- Обязательные поля RaceDescriptor: race_name, creature_cls,
  tick_processor_cls, loader_fn, panel_cls. Остальное - по потребности:
  spawn_manager_cls, spawn_fn, name_pools, creature_placement_modes,
  world_collections, persistence_registry, placeable_objects,
  render_layers, minimap_layers, road_networks, world_tick_fn,
  extra_world_save_fn / extra_world_load_fn, player_tools,
  display_checkboxes, object_panel_extra_fn, secondary_panel_specs,
  landmark_specs, extra_object_collections, biome_cascade_specs,
  mouse_down/up/motion/wheel_hooks, instruction_*.
- Обязательные поля AnimalDescriptor: animal_name, animal_cls, loader_fn,
  spawn_fn, world_collection, save_filename, placement_mode,
  placement_label. Остальное: name_pools, tick_fn, initial_count,
  object_panel_extra_fn, drop_collections, drop_persistence_registry,
  minimap_checkbox_label, minimap_marker_fn, instruction_*.
- Нужной возможности нет в дескрипторе - расширь сам дескриптор и добавь
  чтение поля в ядре. Не обходи прямым импортом.
- Расчистка территории под постройку НЕ через дескриптор: расовый код
  зовёт публичный object_manager.clear_core_objects_in_zone(...).
- Сигнатура mouse-hook: hook(game, event, mouse_x, mouse_y) -> bool
  (True - событие съедено).
- Слои: RenderLayer/MinimapLayer.insert_after - ключ существующего
  core-слоя. Render: roads, road_crossings, landscape, grass,
  water_puddles, bushes, trees, stones, fruits, meat, animal_drops,
  spikes, creatures, animals. Minimap: roads, landscape, water, bushes,
  trees, stones, fruits, spikes, creatures, animals. Слои миникарты
  "creatures" и "animals" перерисовываются каждый кадр, остальные
  кешируются.
- Дополнительная боковая панель (SecondaryPanelSpec) обязана иметь:
  selected, panel_rect, clear(game), handle_click(game, x, y),
  rebuild_layout(w, h), draw(screen). Опционально: popup_active +
  draw_popup + handle_popup_click + close_popup_or_deselect;
  modal_active + handle_event; text_editing + handle_keydown;
  handle_wheel(game, x, y, wheel_y) -> bool.

Чек-лист новой расы: папка creatures/races/<имя>/ с race.py; класс
существа наследует LivingEntity; CreatureTickProcessor с process(ctx)
(обязана поддерживать ДОС по ctx.active_ids); persistence_registry и
world_collections; панель; settings/info расы.

Чек-лист нового животного: папка creatures/animals/<вид>/ с файлами
<вид>.py (класс от CreatureBase + get_drops()), <вид>_settings.py,
<вид>_ai.py (tick-функция с ДОС), <вид>_objects.py (дроп от
AnimalDropResource с drop_collection_attr), names.py, animal.py
(дескриптор). Коллекции, сетки поиска, сохранение, меню, чекбоксы миникарты
и Инструкция подхватываются автоматически.

-------------------------------------------------------------------
3. СУЩЕСТВО: ПОДСИСТЕМЫ, СЛАБЫЕ ССЫЛКИ, STATE-БЛОКИ
-------------------------------------------------------------------

Подсистемы и слабые ссылки
- Существо состоит из подсистем-объектов (needs, social, psyche, aging,
  family, territory, brain, pathfinder, interactions, communication,
  player_reactions). Каждая хранит владельца через WeakOwnerMixin
  (self.c) или WeakEntityMixin (self.entity у ИИ животных).
- Владелец ВСЕГДА слабая ссылка. Не заменяй weakref обычным хранением.
- При удалении существа вызывается release_references(): существо
  обнуляет свои ссылки на подсистемы. У животных AnimalService._release_ai
  обнуляет атрибуты, являющиеся WeakEntityMixin, поэтому кеш ИИ на
  животном (например _grazer_ai) обязан быть именно таким объектом.
- Код, перебирающий список существ, должен переживать существо с
  подсистемами None (пример: _resync_territory_claims).

State-блоки (creatures/races/<раса>/state/*.py)
- Данные существа живут в блоках-наследниках StateBlock (dataclass):
  c.puberty, c.housing, c.roads и т.д. Блок = один домен с одним
  владельцем логики (указан в docstring файла). Блок не хранит ссылку на
  существо; нужные объекты получает параметрами.
- Новое поле расы 'Круг': сначала ищи подходящий блок. Плоское поле на
  Creature допустимо только как часть контракта LivingEntity/CreatureBase/
  общей шины ИИ: id, gender, name, hp, hunger, thirst, energy,
  consciousness, x, y, radius, memory, state, goal_text, panic_active,
  is_talking, is_dead, death_timer, death_cause, temperament,
  base_speed_multiplier, curiosity, relationships, target, decision_timer,
  speed_factor, spike_invuln_timer, fear_timer, fear_source, nav_*, age,
  life_stage, sanity_decay_timer.
- Протокол блока: rolled() - начальное состояние; reset() - ТОЛЬКО если
  его вызывает Creature.die(); to_persisted_dict()/from_persisted_dict() -
  только сохраняемые поля. Ключи совместимы со старыми state.json, не
  переименовывать. Рабочая память ИИ не сохраняется.
- Новый блок регистрируется в пяти местах: state/__init__.py,
  Creature.__init__, Creature.die() (если есть reset), Creature.save()
  (если сохраняется), creature_lifecycle.load_creature_from_state.
- Мягкий лимит - 20 блоков (сейчас 17). Новые блоки - только с разрешения
  автора, блок из 1-2 полей не создавать. Проверка:
  python file_scanner.py --state-audit.

-------------------------------------------------------------------
4. ВЗВЕШЕННЫЙ ИИ: Consideration / pick_best
-------------------------------------------------------------------

- Принятие решений (раса 'Круг' и животные) - Utility AI: каждый вариант
  поведения даёт Consideration(name, score, execute). pick_best() берёт
  не первый подходящий, а тот с наибольшим score, чей execute() реально
  вернул цель (None - пробуем следующий).
- Круг: AdultAI и OlderAI собирают GoalComponent из self.components
  (consider(ctx) возвращает список, элементы могут быть None). ChildAI,
  GrazerAI, WolfAI собирают список из методов _consider_*. Новую линию
  поведения оформляй отдельным компонентом/методом _consider_*, а не
  веткой if/else внутри decide().
- Отсутствие механики у стадии/вида = отсутствие компонента в списке
  (см. раздел 9).
- Контекст тика: DecisionContext (Круг) и WorldFrameContext (ядро) -
  именованные поля с default_factory. Новые данные добавляй полем, а не
  позиционным аргументом. (Исключение исторически: ChildAI.decide.)
- Веса SCORE_* живут атрибутами класса компонента (или модульными
  константами в grazer_ai/wolf_ai/child_ai), не в settings. Шкала:
  85-100 экстренное (выживание, паника, бегство), 55-80 обязательства и
  привязки (сон, партнёр, территория, помощь), 35-50 повседневное (еда,
  вода, стройка), 8-30 фон (дороги, любопытство, блуждание).
- Троттлинг: Creature.decide() реально считает раз в
  ci_settings.AI_DECISION_INTERVAL. Если состояние существа меняется
  извне (игрок, удаление объекта, событие мира) - вызови
  creature.invalidate_plan().
- Общие примитивы (RoamingAnimalMixin, GrazerAI, lookup_creature,
  Consideration, pick_best, scale, clamp01) лежат в
  creatures/all_needed/ai/.

-------------------------------------------------------------------
5. SETTINGS / INFO (числа vs текст)
-------------------------------------------------------------------

- Числа, цвета, тайминги, пороги - в *_settings.py (settings.py для ядра,
  ci_settings.py для Круга, cow/sheep/wolf_settings.py для животных).
- Текст для игрока: info.py (ядро), ci_info.py (Круг; женские варианты
  через INFO_FEMALE_VARIANTS + gendered_text()). У животных нет
  отдельного info-файла: их текст лежит в секции "# Текст" своего
  *_settings.py.
- Тексты Инструкции живут рядом с контентом: race_instruction.py у Круга,
  *_INSTRUCTION_SECTIONS в модуле животного, game/instruction_content.py
  для ядра.
- Новые литералы строк и магические числа в логику не вписывай: заводи
  константу рядом с похожими. Старые исключения (подписи панелей и т.п.)
  не трогай в рамках чужих правок.
- Меняешь баланс - сначала проверь, нет ли готовой константы с похожим
  смыслом.

-------------------------------------------------------------------
6. СОХРАНЕНИЕ / ЗАГРУЗКА МИРА
-------------------------------------------------------------------

- Объект: to_dict()/from_dict(). Существа животных - base_to_dict()/
  apply_base_dict() через CreatureBase. Существо Круга - state-блоки
  (to_persisted_dict/from_persisted_dict) + Creature.save() +
  creature_lifecycle.load_creature_from_state.
- Регистрация сохраняемого типа:
    ядро: _CORE_OBJECT_REGISTRY (game/world_manager.py) +
      WorldState.CORE_COLLECTIONS (game/world_context.py); если объект
      размещаемый - ещё CORE_OBJECT_TYPES (game/object_manager/
      object_types.py);
    раса: persistence_registry + world_collections в RaceDescriptor;
    животное: save_filename/world_collection, дропы -
      drop_collections/drop_persistence_registry.
  Коллекции рас и животных собираются из дескрипторов сами.
- В конце game/world_manager.py есть self-check: реестр сохранения должен
  совпасть с WorldState.COLLECTION_NAMES (без "creatures").
- Родословная (GenealogyRegistry) - отдельный файл genealogy.json,
  сохраняется через extra_world_save_fn/extra_world_load_fn.
- Весь I/O через write_json_atomic (creatures/all_needed/safe_io.py).
  При открытии мира сначала проверяется world.json и обязательные
  файлы (WorldLoadError), и только потом меняется состояние игры.
  Открытый мир копируется в "<мир>.bak". Штамп game_version пишется
  строго последним.
- Версия: единственный источник - GAME_VERSION в settings.py. В world.json
  created_version неизменна, game_version обновляется при сохранении, при
  открытии лежит в game.world_version (на неё опирается любой код
  миграций). GAME_VERSION повышается по просьбе автора; гарантию
  поддержки старых миров автор указывает в промтах.
- Ключи в state.json и именах файлов не переименовывать без миграции.

-------------------------------------------------------------------
7. ПРОИЗВОДИТЕЛЬНОСТЬ
-------------------------------------------------------------------

- Поиск ближайших объектов - через SpatialGrid
  (creatures/all_needed/navigation.py), сетки строит game/simulation.py
  (статические - раз в несколько кадров, существа - чаще, животные - каждый
  кадр). Не пиши линейный перебор world.xxx, если есть сетка.
- ДОС: существа/животные вне зоны камеры (плюс избранное и его окружение)
  замораживаются (tick_frozen_state/should_be_removed в
  creatures/all_needed/simulation_area.py, ctx.active_ids). Новый вид
  или раса ОБЯЗАНЫ это поддерживать.
- A* кешируется (NavGridCache), пересчёт привязан к
  world.landscape_version. Меняешь проходимость (стены, заборы, шипы,
  биом) - увеличь landscape_version.
- Прочие кеши: сварка стен (welded_landscape_polylines), статические слои
  миникарты, троттлинг решений ИИ (раздел 4), gc.freeze() в 1_main.py.

-------------------------------------------------------------------
8. UI И ВВОД
-------------------------------------------------------------------

- Панели ядра (ObjectPanel, AnimalPanel, MinimapPanel, TopBarPanel,
  SettingsPanel, InstructionPanel, WorldScreensPanel, ExitConfirmPanel,
  UIManager) не знают о конкретной расе/животном. Расширение - через
  дескриптор: object_panel_extra_fn, display_checkboxes, minimap_layers,
  secondary_panel_specs, instruction_sections, player_tools, hooks.
- Панель существа своей расы (CreaturePanel и подобные) пишется
  полностью кастомной внутри папки расы и подключается через panel_cls.
- Ввод - пакет game/input_handler/, парный к ui/: каждый модальный экран
  = ScreenLayer; порядок слоёв в InputHandler = приоритет; шаги Escape -
  упорядоченный EscapeStack в WorldLayer.

-------------------------------------------------------------------
9. НИКАКИХ "ЗАГЛУШЕК"
-------------------------------------------------------------------

- Отсутствие возможности выражается отсутствием компонента/метода, а не
  пустым переопределением "на всякий случай" и не комментарием "здесь
  ничего не делаем".
- Допустимо: нулевые реализации в БАЗОВОМ контракте (LivingEntity,
  StateBlock) - это интерфейс по умолчанию. Недопустимо: no-op
  переопределения в наследниках и блоки с методами, которые никто не
  вызывает.
- Заготовка без потребителя (FOOD_CATEGORY_COOKED_MEAT) допустима, если
  в комментарии сказано, почему это не мёртвая ветка и когда она оживёт.

-------------------------------------------------------------------
10. ГЛОБАЛЬНЫЕ ГРАБЛИ
-------------------------------------------------------------------

- settings.WORLD_WIDTH/HEIGHT и WINDOW_WIDTH/HEIGHT меняются при
  открытии мира. Всегда читай их как settings.WORLD_WIDTH; никогда
  "from settings import WORLD_WIDTH" (получишь копию на момент импорта).
- Игровое время - только через dt (секунды; кадр ограничен
  MAX_FRAME_DT). time.time() - для created, мигания UI и подавления
  автосохранения. У Memory собственные игровые часы.
- ID: creatures/all_needed/ids.new_id().
- Генерация мира детерминирована сидом: используй переданный rng или
  seeded_global_random (game/object_manager/generation.py).
- Исключения логики не глотаем: они уходят в крэш-обработчик Game.run
  (экран ошибки + лог в err/). Ловим только OSError на файловом I/O.
- Python 3.10+ (используются типы вида "X | None").

-------------------------------------------------------------------
11. ИНСТРУМЕНТЫ
-------------------------------------------------------------------

- text_maker.py: копирует .py в .txt и строит СКЕЛЕТ.txt и
  СКЕЛЕТ_ПРОДВИНУТЫЙ.txt. Запускай после структурных изменений.
- file_scanner.py (самодостаточный, без внешних планов):
    python file_scanner.py                    - несуществующие атрибуты
                                                существа (по умолчанию)
    python file_scanner.py --state-audit      - оценка state-блоков
    python file_scanner.py --fields a b       - где используются поля
    python file_scanner.py --all              - инвентаризация
  Это эвристика, а не type-checker: не ловит необъявленные имена
  (NameError) - для этого pyflakes/ruff. Запускай после крупных правок
  Creature и state-блоков.

-------------------------------------------------------------------
12. ФОРМАТ ОТВЕТА ПРИ ПРАВКЕ КОДА
-------------------------------------------------------------------

Отвечай обычными подробными сообщениями, без интерактивных элементов и
сторонних инструментов отображения (браузер автора их не показывает).

Когда даёшь фрагмент кода, всегда указывай его место в порядке:

    [Имя файла] -> [Имя класса] (если есть) -> [Имя метода]
    + по желанию [Дополнительный ориентир: рядом с чем, после какой
      строки/комментария]

Пример:
    creatures/races/circles/ai/adult_ai.py -> AdultAI -> __init__
    (добавить новый компонент в self.components)

Правка вне класса/метода - только файл и ближайшая именованная
константа/секция.

-------------------------------------------------------------------
13. ПРОЧИЕ КОНВЕНЦИИ
-------------------------------------------------------------------

- Комментарии на русском, в стиле проекта: короткие
  "# ---------- ... ----------" перед логическим доменом и крупные
  "# =========================================================================" перед
  большими доменами/классами в одном файле.
- Названия существ/животных/ресурсов/UI-текст - только через константы
  (раздел 5).
- Меняешь существующее поведение - упомяни, что именно и почему, и
  проверь соседние места (сохранение, дескриптор, Инструкция).