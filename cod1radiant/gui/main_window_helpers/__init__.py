"""Main window modular components."""

from .menu_builder import create_menus
from .toolbar_builder import create_toolbars, add_toolbar_action, update_toolbar_icon_size
from .dock_builder import create_docks

__all__ = [
    "create_menus",
    "create_toolbars",
    "add_toolbar_action",
    "update_toolbar_icon_size",
    "create_docks",
]
