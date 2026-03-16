"""Dock widget creation for the main window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDockWidget, QTextEdit

from ...config import APP_NAME, APP_VERSION
from ...core import events, FilterChangedEvent

# Import dock panel components
from ..brush_properties import BrushPropertiesPanel
from ..entity_properties_panel import EntityPropertiesPanel
from ..filter_panel import FilterPanel
from ..info_panel import InfoPanel
from ..texture_browser import TextureBrowserPanel
from ..texture_properties import TexturePropertiesPanel

if TYPE_CHECKING:
    from ..main_window import MainWindow


def create_docks(window: "MainWindow") -> None:
    """Create all dock widgets for the main window.

    Args:
        window: The main window instance
    """
    # Console dock
    _create_console_dock(window)

    # Brush properties dock
    _create_brush_properties_dock(window)

    # Texture properties dock
    _create_texture_properties_dock(window)

    # Entity properties dock
    _create_entity_properties_dock(window)

    # Filter panel dock
    _create_filter_dock(window)

    # Info panel dock
    _create_info_dock(window)

    # Texture Browser dock
    _create_texture_browser_dock(window)

    # Add dock toggle actions to Panels menu
    window.panels_menu.addAction(window._brush_dock.toggleViewAction())
    window.panels_menu.addAction(window._texture_dock.toggleViewAction())
    window.panels_menu.addAction(window._entity_dock.toggleViewAction())
    window.panels_menu.addAction(window._filter_dock.toggleViewAction())
    window.panels_menu.addAction(window._info_dock.toggleViewAction())
    window.panels_menu.addAction(window._texture_browser_dock.toggleViewAction())
    window.panels_menu.addAction(window._console_dock.toggleViewAction())

    # Apply initial filters to both viewports via Event (all enabled by default)
    initial_filters = window.filter_panel.get_filters()
    events.publish(FilterChangedEvent(filters=initial_filters))


def _create_console_dock(window: "MainWindow") -> None:
    """Create the console dock widget."""
    window._console_dock = QDockWidget("Console", window)
    window._console_dock.setObjectName("ConsoleDock")
    window._console_widget = QTextEdit()
    window._console_widget.setReadOnly(True)
    window._console_widget.setMinimumHeight(80)
    window._console_widget.setMaximumHeight(200)
    window._apply_console_color()
    window._console_dock.setWidget(window._console_widget)
    window.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, window._console_dock)

    # Log startup message
    window.log_message(f"{APP_NAME} v{APP_VERSION} started")


def _create_brush_properties_dock(window: "MainWindow") -> None:
    """Create the brush properties dock widget."""
    window._brush_dock = QDockWidget("Brush Properties", window)
    window._brush_dock.setObjectName("BrushDock")
    window.brush_properties = BrushPropertiesPanel(window.document)
    window.brush_properties.properties_changed.connect(window._on_brush_properties_changed)
    window._brush_dock.setWidget(window.brush_properties)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window._brush_dock)


def _create_texture_properties_dock(window: "MainWindow") -> None:
    """Create the texture properties dock widget."""
    window._texture_dock = QDockWidget("Texture Properties", window)
    window._texture_dock.setObjectName("TextureDock")
    window.texture_properties = TexturePropertiesPanel(window.document)
    window.texture_properties.properties_changed.connect(window._on_texture_properties_changed)
    window.texture_properties.set_main_window(window)
    window._texture_dock.setWidget(window.texture_properties)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window._texture_dock)


def _create_entity_properties_dock(window: "MainWindow") -> None:
    """Create the entity properties dock widget (with tabs: Properties and Entity Tree)."""
    window._entity_dock = QDockWidget("Entity Properties", window)
    window._entity_dock.setObjectName("EntityDock")
    window.entity_properties = EntityPropertiesPanel()
    window.entity_properties.set_document(window.document)
    window.entity_properties.properties_changed.connect(window._on_entity_properties_changed)
    window.entity_properties.select_entity.connect(window._on_select_entity)
    window.entity_properties.goto_entity.connect(window._on_goto_entity)
    window._entity_dock.setWidget(window.entity_properties)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window._entity_dock)


def _create_filter_dock(window: "MainWindow") -> None:
    """Create the filter panel dock widget."""
    window._filter_dock = QDockWidget("Filter", window)
    window._filter_dock.setObjectName("FilterDock")
    window.filter_panel = FilterPanel()
    window.filter_panel.filters_changed.connect(window._on_filters_changed)
    window._filter_dock.setWidget(window.filter_panel)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window._filter_dock)


def _create_info_dock(window: "MainWindow") -> None:
    """Create the info panel dock widget."""
    window._info_dock = QDockWidget("Info", window)
    window._info_dock.setObjectName("InfoDock")
    window.info_panel = InfoPanel()
    window.info_panel.set_document(window.document)
    window._info_dock.setWidget(window.info_panel)
    window.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, window._info_dock)


def _create_texture_browser_dock(window: "MainWindow") -> None:
    """Create the texture browser dock widget."""
    window._texture_browser_dock = QDockWidget("Texture Browser", window)
    window._texture_browser_dock.setObjectName("TextureBrowserDock")
    window.texture_browser = TextureBrowserPanel()
    window.texture_browser.texture_applied.connect(window._on_texture_applied)
    window._texture_browser_dock.setWidget(window.texture_browser)
    window.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, window._texture_browser_dock)

    # Initialize texture browser from settings
    window._init_texture_browser()
