"""подпапка для разбиения ui.py на соло-компоненты"""

from .constants import BIOME_LABELS, BIOME_PREVIEW_COLOR
from .exit_confirm import ExitConfirmPanel
from .instruction_panel import InstructionPanel
from .manager import UIManager
from .minimap import MinimapPanel
from .object_panel import ObjectPanel
from .settings_panel import SETTINGS_TABS, SettingsPanel
from .top_bar import TopBarPanel
from .world_screens import WorldScreensPanel

__all__ = [
    "BIOME_LABELS",
    "BIOME_PREVIEW_COLOR",
    "SETTINGS_TABS",
    "ExitConfirmPanel",
    "InstructionPanel",
    "MinimapPanel",
    "ObjectPanel",
    "SettingsPanel",
    "TopBarPanel",
    "UIManager",
    "WorldScreensPanel",
]