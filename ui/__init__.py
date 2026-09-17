"""подпапка для разбиения ui.py на соло-компоненты"""

from .manager import UIManager
from .top_bar import TopBarPanel
from .object_panel import ObjectPanel
from .minimap import MinimapPanel
from .world_screens import WorldScreensPanel
from .settings_panel import SettingsPanel, SETTINGS_TABS
from .instruction_panel import InstructionPanel
from .exit_confirm import ExitConfirmPanel
from .constants import BIOME_PREVIEW_COLOR, BIOME_LABELS

__all__ = [
    "UIManager",
    "TopBarPanel",
    "ObjectPanel",
    "MinimapPanel",
    "WorldScreensPanel",
    "SettingsPanel", "SETTINGS_TABS",
    "InstructionPanel",
    "ExitConfirmPanel",
    "BIOME_PREVIEW_COLOR", "BIOME_LABELS",
]