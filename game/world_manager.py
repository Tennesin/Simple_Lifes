import gc
import json
import os
import random
import shutil
import time

import pygame

import info
import settings
from biome import (
    BIOME_RATIO_MAX,
    BIOME_RATIO_MIN,
    BIOME_RATIO_STEP,
    DEFAULT_BIOME_RATIOS,
    adjust_biome_ratio,
    finalize_biome_ratios,
)
from game.animal_registry import all_animal_drop_persistence_entries, all_animals
from game.race_registry import (
    all_extra_world_load_fns,
    all_extra_world_save_fns,
    all_races,
    get_race,
)
from objects import (
    Bush,
    Fence,
    Fruit,
    Grass,
    Meat,
    Road,
    RoadCrossing,
    Spike,
    Stone,
    Tree,
    Wall,
    WaterPuddle,
)
from player import Player
from creatures.all_needed.safe_io import write_json_atomic
from .widgets import ScrollArea, Slider, TextInputBox
from .world_context import WorldState

INVALID_NAME_CHARS = '<>:"/\\|?*'
# ---------- Обязательные поля world.json и обязательные файлы папки мира ----------
_REQUIRED_META_KEYS = (
    "name", "world_width", "world_height", "seed",
    "biome_ratios", "generate_animals", "created_version", "game_version",
)
_REQUIRED_WORLD_FILES = (settings.WORLD_BIOME_FILENAME,)

class WorldLoadError(Exception):
    """Мир нельзя открыть. Текст сообщения предназначен для показа игроку."""

def sanitize_world_name(name):
    if not name:
        return settings.DEFAULT_WORLD_NAME
    for ch in INVALID_NAME_CHARS:
        name = name.replace(ch, "_")
    name = name.strip()
    return name if name else settings.DEFAULT_WORLD_NAME

def get_unique_world_folder_name(base_name):
    base_name = sanitize_world_name(base_name)
    candidate = base_name + settings.WORLD_EXTENSION
    if not os.path.exists(os.path.join(settings.BASE_WORLDS_DIR, candidate)):
        return candidate
    n = 1
    while True:
        candidate = f"{base_name} ({n}){settings.WORLD_EXTENSION}"
        if not os.path.exists(os.path.join(settings.BASE_WORLDS_DIR, candidate)):
            return candidate
        n += 1

def is_valid_world(path):
    if not path or not os.path.isdir(path):
        return False
    if not path.endswith(settings.WORLD_EXTENSION):
        return False
    return os.path.isfile(os.path.join(path, settings.WORLD_META_FILENAME))

# ---------- Состояние экрана "Создание мира" ----------

class CreateWorldScreen:
    def __init__(self):
        self.name_input = TextInputBox(
            pygame.Rect(0, 0, 10, 10), value="", max_len=24,
            placeholder=info.INFO_WS_NAME_PLACEHOLDER)
        self.width_input = TextInputBox(
            pygame.Rect(0, 0, 10, 10), value=str(settings.WORLD_DEFAULT_SIZE[0]),
            max_len=5, digits_only=True, placeholder=info.INFO_WS_SIZE_PLACEHOLDER)
        self.height_input = TextInputBox(
            pygame.Rect(0, 0, 10, 10), value=str(settings.WORLD_DEFAULT_SIZE[1]),
            max_len=5, digits_only=True, placeholder=info.INFO_WS_SIZE_PLACEHOLDER)
        self.seed_input = TextInputBox(
            pygame.Rect(0, 0, 10, 10), value="", max_len=12,
            digits_only=True, placeholder=info.INFO_WS_SEED_PLACEHOLDER)
        self.error_text = None

        self.generate_animals = True

        self.biome_ratios = dict(DEFAULT_BIOME_RATIOS)
        self.biome_sliders = {
            biome: Slider(pygame.Rect(0, 0, 10, 10), value=ratio,
                         min_value=BIOME_RATIO_MIN, max_value=BIOME_RATIO_MAX, step=BIOME_RATIO_STEP)
            for biome, ratio in self.biome_ratios.items()
        }

    def all_inputs(self):
        return (self.name_input, self.width_input, self.height_input, self.seed_input)

    def apply_biome_slider_change(self, biome, new_value):
        self.biome_ratios = adjust_biome_ratio(self.biome_ratios, biome, new_value)
        for b, slider in self.biome_sliders.items():
            slider.value = self.biome_ratios[b]

# ---------- Состояние экрана "Загрузка мира" ----------

class LoadWorldEntry:
    def __init__(self, folder_path, meta):
        self.folder_path = folder_path
        self.meta = meta
        self.folder_name = os.path.basename(folder_path)
        self.counts = None  # заполняется лениво при выборе записи

    @property
    def display_name(self):
        return self.meta.get("name") or self.folder_name


class LoadWorldScreen:
    def __init__(self):
        self.entries = []
        self.selected_index = None
        self.list_scroll = ScrollArea()
        self.info_scroll = ScrollArea()
        self.confirm_delete = False
        self.error_text = None

_CORE_OBJECT_REGISTRY = (
    ("fruits.json", "fruits", Fruit),
    ("spikes.json", "spikes", Spike),
    ("water.json", "water_puddles", WaterPuddle),
    ("bushes.json", "bushes", Bush),
    ("trees.json", "trees", Tree),
    ("stones.json", "stones", Stone),
    ("roads.json", "roads", Road),
    ("walls.json", "walls", Wall),
    ("fences.json", "fences", Fence),
    ("road_crossings.json", "road_crossings", RoadCrossing),
    ("grass.json", "grass", Grass),
    ("meats.json", "meats", Meat),
)

def _collect_race_object_registry():
    entries = []
    seen_attrs = set()
    for descriptor in all_races():
        for entry in descriptor.persistence_registry:
            _filename, attr, _cls = entry
            if attr in seen_attrs:
                continue
            seen_attrs.add(attr)
            entries.append(entry)
    return tuple(entries)

def _collect_animal_object_registry():
    return tuple(
        (descriptor.save_filename, descriptor.world_collection, descriptor.animal_cls)
        for descriptor in all_animals()
    )

def _collect_animal_drop_object_registry():
    return all_animal_drop_persistence_entries()

class WorldManager:
    def __init__(self, game):
        self.game = game
        self._autosave_timer = 0.0

    _WORLD_OBJECT_REGISTRY = (
            _CORE_OBJECT_REGISTRY + _collect_race_object_registry()
            + _collect_animal_object_registry() + _collect_animal_drop_object_registry()
    )

    def _discard_world_state(self):
        """Выбрасывает прежний мир: рвёт циклы существ, чистит коллекции и кэши симуляции."""
        game = self.game
        for creature in game.world.creatures:
            creature.release_references()
        game.world.reset()
        game.simulation.reset_world_caches()
        gc.collect()

    # ---------- Экран создания мира ----------

    def open_create_screen(self):
        game = self.game
        game.close_all_menus()
        game.load_world_screen = None
        game.create_world_screen = CreateWorldScreen()

    def cancel_create_screen(self):
        self.game.create_world_screen = None

    def confirm_create_screen(self):
        game = self.game
        screen = game.create_world_screen
        if screen is None:
            return

        name = screen.name_input.text.strip()
        if not name:
            screen.error_text = info.INFO_WS_ERROR_EMPTY_NAME
            return

        width = self._parse_size(screen.width_input.text)
        height = self._parse_size(screen.height_input.text)
        if width is None or height is None:
            screen.error_text = info.INFO_WS_ERROR_SIZE.format(
                min=settings.WORLD_MIN_SIZE, max=settings.WORLD_MAX_SIZE)
            return

        seed_text = screen.seed_input.text.strip()
        seed = int(seed_text) if seed_text.isdigit() else random.randint(0, 2 ** 31 - 1)

        biome_ratios = dict(screen.biome_ratios)
        generate_animals = screen.generate_animals

        game.create_world_screen = None
        self.create_world(name, width, height, seed,
                          biome_ratios=biome_ratios, generate_animals=generate_animals)

    @staticmethod
    def _parse_size(text):
        if not text or not text.isdigit():
            return None
        value = int(text)
        if value < settings.WORLD_MIN_SIZE or value > settings.WORLD_MAX_SIZE:
            return None
        return value

    # ---------- Экран загрузки мира ----------

    def open_load_screen(self):
        game = self.game
        game.close_all_menus()
        game.create_world_screen = None
        screen = LoadWorldScreen()
        screen.entries = self._scan_worlds()
        game.load_world_screen = screen

    def cancel_load_screen(self):
        self.game.load_world_screen = None

    def _scan_worlds(self):
        os.makedirs(settings.BASE_WORLDS_DIR, exist_ok=True)
        entries = []
        for folder_name in sorted(os.listdir(settings.BASE_WORLDS_DIR)):
            folder_path = os.path.join(settings.BASE_WORLDS_DIR, folder_name)
            if not is_valid_world(folder_path):
                continue
            meta_path = os.path.join(folder_path, settings.WORLD_META_FILENAME)
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except (OSError, json.JSONDecodeError):
                meta = {}
            entries.append(LoadWorldEntry(folder_path, meta))
        return entries

    def select_entry(self, screen, index):
        if index == screen.selected_index:
            return
        screen.selected_index = index
        screen.info_scroll.offset = 0
        screen.confirm_delete = False
        screen.error_text = None
        if 0 <= index < len(screen.entries):
            self._load_entry_counts(screen.entries[index])

    def _load_entry_counts(self, entry):
        if entry.counts is not None:
            return
        counts = {"creatures": 0, "fruits": 0, "spikes": 0,
                  "water": 0, "bushes": 0, "campfires": 0, "roads": 0}

        creatures_dir = os.path.join(entry.folder_path, "creatures")
        if os.path.isdir(creatures_dir):
            counts["creatures"] = sum(
                1 for f in os.listdir(creatures_dir)
                if os.path.isfile(os.path.join(creatures_dir, f, "state.json"))
            )

        # ---------- НОВОЕ: имена файлов больше не переписаны вручную, а берутся
        # из тех же реестров, что и реальное сохранение/загрузка ----------
        file_key_map = (
            ("fruits.json", "fruits"), ("spikes.json", "spikes"),
            ("water.json", "water"), ("bushes.json", "bushes"),
            ("roads.json", "roads"),
        )
        campfire_filename = next(
            (filename for filename, attr, _cls in self._WORLD_OBJECT_REGISTRY if attr == "campfires"),
            None
        )
        if campfire_filename is not None:
            file_key_map = file_key_map + ((campfire_filename, "campfires"),)

        for filename, key in file_key_map:
            path = os.path.join(entry.folder_path, filename)
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        counts[key] = len(json.load(f))
                except (OSError, json.JSONDecodeError):
                    pass

        animals_by_type = {}
        for descriptor in all_animals():
            path = os.path.join(entry.folder_path, descriptor.save_filename)
            count = 0
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        count = len(json.load(f))
                except (OSError, json.JSONDecodeError):
                    count = 0
            animals_by_type[descriptor.animal_name] = count
        counts["animals_total"] = sum(animals_by_type.values())
        counts["animals_by_type"] = animals_by_type

        entry.counts = counts

    def load_selected(self, screen):
        if screen.selected_index is None:
            return
        entry = screen.entries[screen.selected_index]
        try:
            self.open_world(entry.folder_path, is_new=False)
        except WorldLoadError as error:
            screen.error_text = str(error)
            return
        self.game.load_world_screen = None

    def delete_selected(self, screen):
        if screen.selected_index is None:
            return
        if not screen.confirm_delete:
            screen.confirm_delete = True
            return
        entry = screen.entries[screen.selected_index]
        shutil.rmtree(entry.folder_path, ignore_errors=True)
        shutil.rmtree(entry.folder_path + ".bak", ignore_errors=True)
        screen.entries = self._scan_worlds()
        screen.selected_index = None
        screen.confirm_delete = False

    # ---------- Создание/открытие мира ----------

    def create_world(self, name, width=None, height=None, seed=None,
                     biome_ratios=None, generate_animals=True):
        os.makedirs(settings.BASE_WORLDS_DIR, exist_ok=True)
        folder_name = get_unique_world_folder_name(name)
        world_path = os.path.join(settings.BASE_WORLDS_DIR, folder_name)
        os.makedirs(world_path, exist_ok=True)
        os.makedirs(os.path.join(world_path, "creatures"), exist_ok=True)

        width = width or settings.WORLD_DEFAULT_SIZE[0]
        height = height or settings.WORLD_DEFAULT_SIZE[1]
        if seed is None:
            seed = random.randint(0, 2 ** 31 - 1)

        biome_ratios = finalize_biome_ratios(biome_ratios or DEFAULT_BIOME_RATIOS, rng=random.Random(seed))

        meta = {
            "name": sanitize_world_name(name),
            "created": time.time(),
            "created_version": settings.GAME_VERSION,
            "game_version": settings.GAME_VERSION,
            "world_width": width,
            "world_height": height,
            "seed": seed,
            "biome_ratios": biome_ratios,
            "generate_animals": generate_animals,
        }
        with open(os.path.join(world_path, settings.WORLD_META_FILENAME), "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        self.open_world(world_path, is_new=True)

    # ---------- Проверка мира ДО того, как игра начнёт менять своё состояние ----------

    @staticmethod
    def _read_world_meta(world_path):
        meta_path = os.path.join(world_path, settings.WORLD_META_FILENAME)
        if not os.path.exists(meta_path):
            raise WorldLoadError(info.INFO_LW_ERROR_MISSING_FILE.format(file=settings.WORLD_META_FILENAME))
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        except (OSError, json.JSONDecodeError):
            raise WorldLoadError(info.INFO_LW_ERROR_META_BROKEN.format(file=settings.WORLD_META_FILENAME))
        for key in _REQUIRED_META_KEYS:
            if key not in meta:
                raise WorldLoadError(
                    info.INFO_LW_ERROR_META_KEY.format(file=settings.WORLD_META_FILENAME, key=key))
        return meta

    @staticmethod
    def _check_world_files(world_path):
        for filename in _REQUIRED_WORLD_FILES:
            if not os.path.exists(os.path.join(world_path, filename)):
                raise WorldLoadError(info.INFO_LW_ERROR_MISSING_FILE.format(file=filename))

    def open_world(self, world_path, is_new):
        game = self.game

        # ---------- Сначала проверяем мир, и только потом трогаем состояние игры ----------
        meta = self._read_world_meta(world_path)
        if not is_new:
            self._check_world_files(world_path)

        game.simulation.invalidate_nav_cache()
        if game.world_loaded and game.world_path and game.display_settings.get("autosave_enabled", True):
            self.save_world()

        game.world_loaded = False

        world_width = meta["world_width"]
        world_height = meta["world_height"]
        world_seed = meta["seed"]

        settings.WORLD_WIDTH = world_width
        settings.WORLD_HEIGHT = world_height

        game.world_path = world_path
        game.world_seed = world_seed
        game.world_version = meta["game_version"]
        self._discard_world_state()
        for fn in all_extra_world_load_fns():
            fn(game)
        game.clear_secondary_selections()
        game.resize_for_world(world_width, world_height)
        game.placement_mode = None
        game.paused = False
        game.selected_creature = None
        game.selected_object = None
        game.editing_name = False
        game.name_edit_buffer = ""
        game.player = Player()
        game.favorite_id = None
        game.close_all_menus()

        if is_new:
            game.biome_manager.generate(world_width, world_height, world_seed, ratios=meta["biome_ratios"])
            game.object_manager.generate_initial_resources(world_seed)
            if meta["generate_animals"]:
                game.object_manager.generate_initial_animals(world_seed)
            self.save_world()
        else:
            self.load_world_data()
            self._make_session_backup(world_path)

        self._autosave_timer = 0.0
        game.world_loaded = True

    def load_world_data(self):
        game = self.game
        creatures_dir = os.path.join(game.world_path, "creatures")
        if os.path.isdir(creatures_dir):
            for folder in os.listdir(creatures_dir):
                folder_path = os.path.join(creatures_dir, folder)
                state_file = os.path.join(folder_path, "state.json")
                mem_file = os.path.join(folder_path, "memory.json")
                if os.path.isdir(folder_path) and os.path.exists(state_file):
                    with open(state_file, "r", encoding="utf-8") as f:
                        state = json.load(f)
                    descriptor = get_race(state["race"])
                    creature = descriptor.loader_fn(state)
                    if os.path.exists(mem_file) and hasattr(creature, "memory"):
                        creature.memory.load(mem_file)
                    game.world.creatures.append(creature)

        for filename, attr, cls in self._WORLD_OBJECT_REGISTRY:
            path = os.path.join(game.world_path, filename)
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                setattr(game.world, attr, [cls.from_dict(d) for d in data])

        biome_path = os.path.join(game.world_path, settings.WORLD_BIOME_FILENAME)
        with open(biome_path, "r", encoding="utf-8") as f:
            game.biome_manager.load_from_dict(json.load(f))

        for creature in game.world.creatures:
            creature.territory.sync_claims_count(game.world.bushes, game.world.water_puddles)

        self._load_player_state()
        game.world.landscape_version += 1

    def _load_player_state(self):
        game = self.game
        path = os.path.join(game.world_path, "player_state.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        game.favorite_id = data.get("favorite_id")

    # ---------- Сохранение ----------

    def save_world(self):
        game = self.game
        if not game.world_path:
            return
        creatures_dir = os.path.join(game.world_path, "creatures")
        os.makedirs(creatures_dir, exist_ok=True)
        for creature in game.world.creatures:
            creature.save(creatures_dir)

        for filename, attr, _cls in self._WORLD_OBJECT_REGISTRY:
            items = getattr(game.world, attr)
            write_json_atomic(os.path.join(game.world_path, filename),
                              [obj.to_dict() for obj in items], indent=2)
        if game.biome_manager.grid is not None:
            write_json_atomic(os.path.join(game.world_path, settings.WORLD_BIOME_FILENAME),
                              game.biome_manager.to_dict())
        self._save_player_state()
        for fn in all_extra_world_save_fns():
            fn(game)

        # ---------- Штамп версии - строго последним ----------
        self._stamp_world_version()

    def _stamp_world_version(self):
        game = self.game
        meta_path = os.path.join(game.world_path, settings.WORLD_META_FILENAME)
        # ---------- Папка без world.json миром не считается (см. is_valid_world) - штамповать нечего ----------
        if not os.path.exists(meta_path):
            return
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["game_version"] = settings.GAME_VERSION

        # ---------- Через временный файл, чтобы обрыв записи не оставил битый world.json ----------
        tmp_path = meta_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, meta_path)

    # ---------- ДОС: избранное существо переживает перезапуск игры ----------
    def _save_player_state(self):
        game = self.game
        path = os.path.join(game.world_path, "player_state.json")
        try:
            write_json_atomic(path, {"favorite_id": game.favorite_id}, indent=2)
        except OSError:
            pass

    def save_world_manual(self):
        game = self.game
        if not game.world_loaded:
            return
        self.save_world()
        self._autosave_timer = 0.0
        game.last_manual_save_time = time.time()
        game.show_game_menu = False

    def _make_session_backup(self, world_path):
        """Копия мира в том виде, в каком его открыли."""
        backup_path = world_path + ".bak"
        try:
            shutil.rmtree(backup_path, ignore_errors=True)
            shutil.copytree(world_path, backup_path, ignore=shutil.ignore_patterns("*.tmp"))
        except OSError:
            pass

    def tick_autosave(self, dt):
        """Фоновое автосохранение. Вызывается каждый кадр из Game.run."""
        game = self.game
        if not game.world_loaded or not game.display_settings.get("autosave_enabled", True):
            self._autosave_timer = 0.0
            return
        self._autosave_timer += dt
        if self._autosave_timer < settings.AUTOSAVE_INTERVAL_SECONDS:
            return
        self._autosave_timer = 0.0
        try:
            self.save_world()
        except OSError:
            pass    # диск полон/файл занят - не роняем игру, попробуем в следующий раз

    def close_world(self, save=None):
        game = self.game
        game.simulation.invalidate_nav_cache()
        if game.world_loaded and game.world_path:
            if save is None:
                suppress_autosave = (
                        game.last_manual_save_time is not None and
                        time.time() - game.last_manual_save_time < settings.MANUAL_SAVE_AUTOSAVE_SUPPRESS_TIME
                )
                save = not suppress_autosave and game.display_settings.get("autosave_enabled", True)
            if save:
                self.save_world()

        self._discard_world_state()
        game.clear_secondary_selections()
        game.placement_mode = None
        game.paused = False
        game.selected_creature = None
        game.selected_object = None
        game.editing_name = False
        game.name_edit_buffer = ""
        game.player = Player()
        game.favorite_id = None
        game.close_all_menus()
        game.last_manual_save_time = None
        game.world_loaded = False
        game.world_path = None
        game.world_version = None
        self._autosave_timer = 0.0

        settings.WORLD_WIDTH, settings.WORLD_HEIGHT = settings.WORLD_DEFAULT_SIZE
        game.restore_default_window()

_registry_attrs = {attr for _, attr, _ in WorldManager._WORLD_OBJECT_REGISTRY}
_expected_attrs = set(WorldState.COLLECTION_NAMES) - {"creatures"}
if _registry_attrs != _expected_attrs:
    raise RuntimeError(
        f"WorldManager._WORLD_OBJECT_REGISTRY разошёлся с WorldState.COLLECTION_NAMES: "
        f"в реестре лишние {_registry_attrs - _expected_attrs}, "
        f"не хватает {_expected_attrs - _registry_attrs}"
    )