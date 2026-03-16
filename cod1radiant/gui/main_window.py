"""Main application window."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtCore import Qt, QSettings, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QKeySequence, QCloseEvent, QShortcut
from PyQt6.QtWidgets import (
    QMainWindow,
    QMenuBar,
    QMenu,
    QToolBar,
    QStatusBar,
    QDockWidget,
    QFileDialog,
    QMessageBox,
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTextEdit,
    QProgressDialog,
    QApplication,
)

from ..config import APP_NAME, APP_VERSION, UI_STYLESHEETS, STYLESHEET_DARK, STYLESHEET_COMPACT, STYLESHEET_SEMI_COMPACT

# Use new core module
from ..core import (
    MapDocument,
    Entity,
    Brush,
    events,
    SelectionChangedEvent,
    DocumentLoadedEvent,
    DocumentModifiedEvent,
    BrushGeometryModifiedEvent,
    PatchGeometryModifiedEvent,
    FilterChangedEvent,
    GridSizeChangedEvent,
    ViewModeChangedEvent,
    ViewportRefreshEvent,
    BrushCreatedEvent,
    BrushDeletedEvent,
    EntityCreatedEvent,
    create_entity,
)

# Import controllers
from .controllers import FileController, EditController, ViewController, BrushController

# Import modular builders
from .main_window_helpers import create_menus, create_toolbars, update_toolbar_icon_size, create_docks

# Import dialogs
from .dialogs import SettingsDialog

# Import texture manager
from ..core.texture_manager import get_texture_manager

if TYPE_CHECKING:
    from .viewport_2d import Viewport2DGL
    from .viewport_3d import Viewport3D


class MainWindow(QMainWindow):
    """Main application window for CoD1 Radiant Editor."""

    # Qt Signal for selection changes
    selection_changed = pyqtSignal()

    # View modes: Top (XY), Front (XZ), Side (YZ)
    VIEW_MODES = ['xy', 'xz', 'yz']
    VIEW_NAMES = {'xy': 'Top (XY)', 'xz': 'Front (XZ)', 'yz': 'Side (YZ)'}

    def __init__(self):
        super().__init__()

        # Create new document using core
        self.document = MapDocument.new()

        self._settings = QSettings("CoD1Radiant", "Editor")
        self._current_view_index = 0  # Start with Top (XY)

        # Viewport placeholders (set in _setup_ui)
        self.viewport_2d: "Viewport2DGL | None" = None
        self.viewport_3d: "Viewport3D | None" = None

        self._setup_ui()

        # Initialize controllers early (needed by menus for recent files)
        self._setup_controllers()

        # Use modular builders
        create_menus(self)
        create_toolbars(self)
        create_docks(self)
        self._create_statusbar()
        self._setup_shortcuts()
        self._apply_theme()

        # Load settings (after controllers are ready)
        self._load_settings()

        # Subscribe to events
        self._setup_event_subscriptions()

        self._update_title()
        self._update_view_label()

    def _setup_controllers(self) -> None:
        """Initialize controller instances."""
        self.file_controller = FileController(self)
        self.edit_controller = EditController(self)
        self.view_controller = ViewController(self)
        self.brush_controller = BrushController(self)

    def _setup_ui(self) -> None:
        """Set up the main UI layout."""
        self.setWindowTitle(f"{APP_NAME} {APP_VERSION}")
        self.setMinimumSize(1024, 768)

        # Create central widget with viewports
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Create splitter for 2D and 3D viewports
        self.viewport_splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(self.viewport_splitter)

        # Create single 2D viewport (switchable) - using ModernGL version
        from .viewport_2d import Viewport2DGL
        from .viewport_3d import Viewport3D

        self.viewport_2d = Viewport2DGL(self.document, axis='xy')
        self.viewport_3d = Viewport3D(self.document)

        self.viewport_splitter.addWidget(self.viewport_2d)
        self.viewport_splitter.addWidget(self.viewport_3d)

        # Set initial sizes (50/50)
        self.viewport_splitter.setSizes([500, 500])

        # Connect Qt signal to slot for proper thread-safe updates
        self.selection_changed.connect(self._do_selection_update)

        # Connect geometry changed signals to update properties panel
        self.viewport_2d.geometry_changed.connect(self._on_geometry_changed)
        self.viewport_3d.geometry_changed.connect(self._on_geometry_changed)

        # Connect entity creation signal from 2D viewport
        self.viewport_2d.create_entity_requested.connect(self._on_create_entity_requested)

    def _setup_event_subscriptions(self) -> None:
        """Subscribe to Event-Bus events."""
        events.subscribe(SelectionChangedEvent, self._on_selection_changed_event)
        events.subscribe(DocumentModifiedEvent, self._on_document_modified_event)
        events.subscribe(GridSizeChangedEvent, self._on_grid_size_changed_event)
        events.subscribe(ViewModeChangedEvent, self._on_view_mode_changed_event)

    # =========================================================================
    # Event Handlers (Event-Bus)
    # =========================================================================

    def _on_selection_changed_event(self, event: SelectionChangedEvent) -> None:
        """Handle selection changes from the event bus."""
        total = len(event.selected_brushes)
        self.selection_label.setText(f"Selection: {total}")

        if hasattr(self, 'properties_panel'):
            self.properties_panel.update_from_selection()

    def _on_document_modified_event(self, event: DocumentModifiedEvent) -> None:
        """Handle document modification state changes."""
        self._update_title()

    def _on_grid_size_changed_event(self, event: GridSizeChangedEvent) -> None:
        """Handle grid size changes."""
        self.grid_label.setText(f"Grid: {event.grid_size}")

    def _on_view_mode_changed_event(self, event: ViewModeChangedEvent) -> None:
        """Handle 2D view mode changes."""
        view_name = self.VIEW_NAMES.get(event.axis, event.axis.upper())
        self.view_label.setText(f"View: {view_name}")

    def _setup_shortcuts(self) -> None:
        """Set up keyboard shortcuts."""
        # Ctrl+Tab to cycle through 2D views
        cycle_view_shortcut = QShortcut(QKeySequence("Ctrl+Tab"), self)
        cycle_view_shortcut.activated.connect(self._cycle_2d_view)

        # Shift+Ctrl+Tab to cycle backwards
        cycle_view_back_shortcut = QShortcut(QKeySequence("Ctrl+Shift+Tab"), self)
        cycle_view_back_shortcut.activated.connect(self._cycle_2d_view_back)

        # Rotation shortcuts
        rotate_z_cw = QShortcut(QKeySequence("R"), self)
        rotate_z_cw.activated.connect(lambda: self._rotate_selection('z', 15))

        rotate_z_ccw = QShortcut(QKeySequence("Shift+R"), self)
        rotate_z_ccw.activated.connect(lambda: self._rotate_selection('z', -15))

        rotate_x_cw = QShortcut(QKeySequence("Ctrl+R"), self)
        rotate_x_cw.activated.connect(lambda: self._rotate_selection('x', 15))

        rotate_y_cw = QShortcut(QKeySequence("Alt+R"), self)
        rotate_y_cw.activated.connect(lambda: self._rotate_selection('y', 15))

        # Scale shortcuts
        scale_up = QShortcut(QKeySequence("Ctrl+]"), self)
        scale_up.activated.connect(lambda: self._scale_selection(1.1))

        scale_down = QShortcut(QKeySequence("Ctrl+["), self)
        scale_down.activated.connect(lambda: self._scale_selection(0.9))

        # Delete shortcut (Backspace as alternative to Delete)
        delete_backspace = QShortcut(QKeySequence("Backspace"), self)
        delete_backspace.activated.connect(self._on_delete)

        # Duplicate shortcut
        duplicate_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        duplicate_shortcut.activated.connect(self._on_duplicate)

    def _cycle_2d_view(self) -> None:
        """Cycle to the next 2D view mode."""
        self._current_view_index = (self._current_view_index + 1) % len(self.VIEW_MODES)
        self._apply_view_mode()

    def _cycle_2d_view_back(self) -> None:
        """Cycle to the previous 2D view mode."""
        self._current_view_index = (self._current_view_index - 1) % len(self.VIEW_MODES)
        self._apply_view_mode()

    def _apply_view_mode(self) -> None:
        """Apply the current view mode to the 2D viewport."""
        axis = self.VIEW_MODES[self._current_view_index]
        self.viewport_2d.set_axis(axis)
        self._update_view_label()
        self.statusBar().showMessage(f"Switched to {self.VIEW_NAMES[axis]}", 2000)

    def _update_view_label(self) -> None:
        """Update the view mode label in the status bar."""
        axis = self.VIEW_MODES[self._current_view_index]
        self.view_label.setText(f"View: {self.VIEW_NAMES[axis]}")

    def _set_view_mode(self, index: int) -> None:
        """Set the 2D view mode directly."""
        self._current_view_index = index
        self._apply_view_mode()

    def _update_toolbar_icon_size(self) -> None:
        """Update toolbar icon sizes based on UI density setting."""
        update_toolbar_icon_size(self)

    def _create_statusbar(self) -> None:
        """Create the status bar."""
        statusbar = self.statusBar()

        self.view_label = QLabel("View: Top (XY)")
        statusbar.addPermanentWidget(self.view_label)

        self.grid_label = QLabel("Grid: 8")
        statusbar.addPermanentWidget(self.grid_label)

        self.position_label = QLabel("X: 0  Y: 0  Z: 0")
        statusbar.addPermanentWidget(self.position_label)

        self.selection_label = QLabel("Selection: 0 brushes")
        statusbar.addPermanentWidget(self.selection_label)

    def _update_title(self) -> None:
        """Update the window title based on document state."""
        title = f"{APP_NAME} {APP_VERSION}"

        if self.document.filepath:
            title += f" - {self.document.filepath.name}"
        else:
            title += " - Untitled"

        if self.document.modified:
            title += " *"

        self.setWindowTitle(title)

    def _update_recent_menu(self) -> None:
        """Update the recent files menu from FileController's list."""
        self.recent_menu.clear()

        recent_files = self.file_controller.get_recent_files()
        for filepath in recent_files[:10]:
            action = QAction(filepath, self)
            action.triggered.connect(lambda checked, f=filepath: self._load_recent_file(f))
            self.recent_menu.addAction(action)

        if not recent_files:
            no_recent = QAction("(No recent files)", self)
            no_recent.setEnabled(False)
            self.recent_menu.addAction(no_recent)

    def _load_recent_file(self, filepath: str) -> None:
        """Load a file from the recent files menu."""
        if self.file_controller.load_file(filepath):
            stats = self.document.get_statistics()
            self.log_message(f"Loaded: {Path(filepath).name}", "success")
            self.log_message(
                f"  Geometry: {stats['brush_count']} brushes, {stats['patch_count']} patches",
                "info"
            )

    def _load_settings(self) -> None:
        """Load application settings."""
        geometry = self._settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self._settings.value("windowState")
        if state:
            self.restoreState(state)

        # Recent files are managed by FileController
        self._update_recent_menu()

    def _save_settings(self) -> None:
        """Save application settings."""
        self._settings.setValue("geometry", self.saveGeometry())
        self._settings.setValue("windowState", self.saveState())

    # =========================================================================
    # Menu actions
    # =========================================================================

    def _on_new(self) -> None:
        """Create a new document."""
        if self.file_controller.new_document():
            self.log_message("New document created", "success")

    def _on_open(self) -> None:
        """Open a file dialog to load a map."""
        if self.file_controller.open_document():
            stats = self.document.get_statistics()
            self.log_message(f"Loaded: {self.document.filepath.name if self.document.filepath else 'unknown'}", "success")
            self.log_message(f"  Geometry: {stats['brush_count']} brushes, {stats['patch_count']} patches", "info")

    def _on_save(self) -> bool:
        """Save the current document."""
        if self.file_controller.save_document():
            self.log_message(f"Saved: {self.document.filepath.name if self.document.filepath else 'unknown'}", "success")
            self._update_title()
            return True
        return False

    def _on_save_as(self) -> bool:
        """Save the document with a new name."""
        if self.file_controller.save_document_as():
            self.log_message(f"Saved: {self.document.filepath.name if self.document.filepath else 'unknown'}", "success")
            self._update_title()
            return True
        return False

    def _on_undo(self) -> None:
        """Undo the last action."""
        if self.edit_controller.undo():
            self._update_title()
            events.publish(BrushGeometryModifiedEvent(
                brush_ids=frozenset(),
                modification_type="undo"
            ))

    def _on_redo(self) -> None:
        """Redo the last undone action."""
        if self.edit_controller.redo():
            self._update_title()
            events.publish(BrushGeometryModifiedEvent(
                brush_ids=frozenset(),
                modification_type="redo"
            ))

    def _on_deselect(self) -> None:
        """Deselect all."""
        self.edit_controller.deselect_all(source="main_window")

    def _on_grid_larger(self) -> None:
        """Increase grid size."""
        self.view_controller.grid_size_up()

    def _on_grid_smaller(self) -> None:
        """Decrease grid size."""
        self.view_controller.grid_size_down()

    def _on_about(self) -> None:
        """Show about dialog."""
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME} {APP_VERSION}\n\n"
            "A modern 3D level editor for Call of Duty 1.\n\n"
            "Compatible with the .MAP file format.\n\n"
            "Shortcuts:\n"
            "  Ctrl+Tab - Cycle 2D views\n"
            "  Ctrl+1/2/3 - Top/Front/Side view"
        )

    def _refresh_viewports(self, progress_callback=None) -> None:
        """Refresh all viewports."""
        self.viewport_2d.set_document(self.document)
        self.viewport_2d.update()
        self.viewport_3d.set_document(self.document, progress_callback)
        self.viewport_3d.update()

    def _on_selection_changed(self) -> None:
        """Handle selection changes - emit signal for Qt event loop."""
        self.selection_changed.emit()

    def _do_selection_update(self) -> None:
        """Actually perform the viewport updates (called via Qt signal)."""
        self.brush_properties.update_from_selection()
        self.texture_properties.update_from_selection()
        self.entity_properties.update_from_selection()

        count = self.document.selection.selected_brush_count
        if count == 0:
            self.statusBar().showMessage("Ready")
        elif count == 1:
            self.statusBar().showMessage("1 brush selected")
        else:
            self.statusBar().showMessage(f"{count} brushes selected")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        if self.file_controller.check_save_before_close():
            self._save_settings()
            event.accept()
        else:
            event.ignore()

    def _rotate_selection(self, axis: str, angle: float) -> None:
        """Rotate all selected brushes around their collective center."""
        selected = self.document.selection.selected_brushes
        if not selected:
            self.statusBar().showMessage("No selection to rotate", 2000)
            return

        self.edit_controller.rotate_selected(axis, angle)

        events.publish(BrushGeometryModifiedEvent(
            brush_ids=selected,
            modification_type="rotate"
        ))
        self.statusBar().showMessage(f"Rotated {len(selected)} brush(es) by {angle}° around {axis.upper()}", 2000)

    def _scale_selection(self, factor: float) -> None:
        """Scale all selected brushes around their collective center."""
        selected = self.document.selection.selected_brushes
        if not selected:
            self.statusBar().showMessage("No selection to scale", 2000)
            return

        self.edit_controller.scale_selected(factor)

        events.publish(BrushGeometryModifiedEvent(
            brush_ids=selected,
            modification_type="scale"
        ))
        percent = int(factor * 100)
        self.statusBar().showMessage(f"Scaled {len(selected)} brush(es) to {percent}%", 2000)

    def _on_delete(self) -> None:
        """Delete all selected brushes."""
        selected = self.document.selection.selected_brushes
        if not selected:
            self.statusBar().showMessage("No selection to delete", 2000)
            return

        count = self.edit_controller.delete_selected()

        events.publish(ViewportRefreshEvent(source="delete", rebuild_geometry=True))
        self._update_title()
        self.info_panel.update_statistics()
        self.statusBar().showMessage(f"Deleted {count} brush(es)", 2000)
        self.log_message(f"Deleted {count} brush(es)")

    def _on_duplicate(self) -> None:
        """Duplicate all selected brushes."""
        selected = self.document.selection.selected_brushes
        if not selected:
            self.statusBar().showMessage("No selection to duplicate", 2000)
            return

        count = self.edit_controller.duplicate_selected()

        current_filters = self.filter_panel.get_filters()
        events.publish(FilterChangedEvent(filters=current_filters))
        events.publish(BrushGeometryModifiedEvent(
            brush_ids=frozenset(),
            modification_type="duplicate"
        ))
        self.info_panel.update_statistics()

        self.statusBar().showMessage(f"Duplicated {count} brush(es)", 2000)

    def _create_primitive(self, primitive_type: str) -> None:
        """Create a primitive brush at the current view center."""
        brush = self.brush_controller.create_primitive_at_viewport_center(primitive_type)

        if brush is None:
            self.statusBar().showMessage(f"Failed to create {primitive_type}", 2000)
            return

        current_filters = self.filter_panel.get_filters()
        events.publish(FilterChangedEvent(filters=current_filters))
        events.publish(BrushGeometryModifiedEvent(
            brush_ids=frozenset(),
            modification_type="create"
        ))
        self.info_panel.update_statistics()

        self.statusBar().showMessage(f"Created {primitive_type}", 2000)
        self.log_message(f"Created {primitive_type}")

    def _on_geometry_changed(self) -> None:
        """Handle geometry changes from viewport drag/edge operations."""
        self.brush_properties.update_from_selection()
        self.texture_properties.update_from_selection()
        self._update_title()
        current_filters = self.filter_panel.get_filters()
        events.publish(FilterChangedEvent(filters=current_filters))

    def _on_brush_properties_changed(self) -> None:
        """Handle brush properties changes from the properties panel."""
        self._update_title()
        selected = self.document.selection.selected_brushes
        events.publish(BrushGeometryModifiedEvent(
            brush_ids=selected,
            modification_type="properties"
        ))

    def _on_texture_properties_changed(self) -> None:
        """Handle texture properties changes from the texture panel."""
        self._update_title()
        events.publish(ViewportRefreshEvent(source="texture_properties"))

    def _on_entity_properties_changed(self) -> None:
        """Handle entity properties changes from the entity properties panel."""
        self._update_title()
        events.publish(ViewportRefreshEvent(source="entity_properties"))

    def _on_filters_changed(self, filters: dict) -> None:
        """Handle filter changes from the filter panel."""
        self.log_message(f"Filters updated: {sum(filters.values())}/{len(filters)} active")

    def _on_preferences(self) -> None:
        """Open the preferences dialog."""
        dialog = SettingsDialog(self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self) -> None:
        """Handle settings changes from the preferences dialog."""
        self._apply_theme()
        self._apply_settings_to_viewports()
        self.statusBar().showMessage("Settings applied", 2000)

    def _apply_settings_to_viewports(self) -> None:
        """Apply current settings to all viewports."""
        self.viewport_2d.reload_settings()
        self.viewport_3d.reload_settings()
        self._apply_console_color()

    def _apply_console_color(self) -> None:
        """Apply console background color from settings."""
        settings = QSettings("CoD1Radiant", "Editor")
        color_value = settings.value("colors/console")
        theme = settings.value("colors/theme", "dark", type=str)

        text_color = "#ccc" if theme == "dark" else "#1e1e1e"

        if color_value and isinstance(color_value, (list, tuple)) and len(color_value) >= 3:
            try:
                r = int(float(color_value[0]) * 255)
                g = int(float(color_value[1]) * 255)
                b = int(float(color_value[2]) * 255)
                self._console_widget.setStyleSheet(
                    f"QTextEdit {{ background-color: rgb({r}, {g}, {b}); color: {text_color}; "
                    f"border: none; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }}"
                )
            except (ValueError, TypeError):
                self._console_widget.setStyleSheet(
                    f"QTextEdit {{ background-color: rgb(30, 30, 30); color: {text_color}; "
                    f"border: none; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }}"
                )
        else:
            self._console_widget.setStyleSheet(
                f"QTextEdit {{ background-color: rgb(30, 30, 30); color: {text_color}; "
                f"border: none; font-family: 'Consolas', 'Courier New', monospace; font-size: 12px; }}"
            )

    def log_message(self, message: str, level: str = "info") -> None:
        """Log a message to the console."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        settings = QSettings("CoD1Radiant", "Editor")
        theme = settings.value("colors/theme", "dark", type=str)

        if theme == "dark":
            colors = {
                "info": "#cccccc",
                "warning": "#ffaa00",
                "error": "#ff5555",
                "success": "#55ff55",
            }
            timestamp_color = "#888888"
        else:
            colors = {
                "info": "#333333",
                "warning": "#aa6600",
                "error": "#cc0000",
                "success": "#008800",
            }
            timestamp_color = "#666666"

        color = colors.get(level, colors["info"])

        formatted = f'<span style="color: {timestamp_color};">[{timestamp}]</span> <span style="color: {color};">{message}</span>'

        self._console_widget.append(formatted)

        scrollbar = self._console_widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _apply_theme(self) -> None:
        """Apply the UI theme stylesheet to the application."""
        theme = self._settings.value("colors/theme", "dark", type=str)
        ui_density = self._settings.value("colors/uiDensity", "semi_compact", type=str)

        if theme == "custom":
            custom_path = self._settings.value("colors/customStylesheet", "", type=str)
            if custom_path and Path(custom_path).exists():
                try:
                    with open(custom_path, "r", encoding="utf-8") as f:
                        stylesheet = f.read()
                    self.log_message(f"Loaded custom stylesheet: {custom_path}", "success")
                except Exception as e:
                    self.log_message(f"Failed to load custom stylesheet: {e}", "error")
                    stylesheet = STYLESHEET_DARK
            else:
                self.log_message("Custom stylesheet path not set or file not found", "warning")
                stylesheet = STYLESHEET_DARK
        else:
            stylesheet = UI_STYLESHEETS.get(theme, STYLESHEET_DARK)

        if ui_density == "compact":
            stylesheet = stylesheet + STYLESHEET_COMPACT
        elif ui_density == "semi_compact":
            stylesheet = stylesheet + STYLESHEET_SEMI_COMPACT

        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet)

    def _on_select_entity(self, entity_idx: int) -> None:
        """Handle entity selection from the entity list panel."""
        if entity_idx >= len(self.document.entities):
            return

        entity = self.document.entities[entity_idx]

        center = entity.get_center()
        if center is None:
            self.statusBar().showMessage("Entity has no position", 2000)
            return

        self.document.selection.clear()

        if entity.brushes:
            for brush_idx in range(len(entity.brushes)):
                self.document.selection.select_brush(entity_idx, brush_idx)
        else:
            self.document.selection.select_entity(entity_idx)

        axis = self.viewport_2d.axis
        if axis == 'xy':
            self.viewport_2d.offset_x = center.x
            self.viewport_2d.offset_y = center.y
        elif axis == 'xz':
            self.viewport_2d.offset_x = center.x
            self.viewport_2d.offset_y = center.z
        else:
            self.viewport_2d.offset_x = center.y
            self.viewport_2d.offset_y = center.z

        events.publish(ViewportRefreshEvent(source="select_entity"))

        self.statusBar().showMessage(f"Selected {entity.classname}", 2000)

    def _on_goto_entity(self, entity_idx: int) -> None:
        """Handle go-to-position from the entity list panel."""
        if entity_idx >= len(self.document.entities):
            return

        entity = self.document.entities[entity_idx]

        center = entity.get_center()
        if center is None:
            self.statusBar().showMessage("Entity has no position", 2000)
            return

        offset_distance = 256.0

        self.viewport_3d.camera.position = np.array([
            center.x - offset_distance,
            center.y - offset_distance,
            center.z + offset_distance / 2
        ], dtype=np.float32)

        target = np.array([center.x, center.y, center.z], dtype=np.float32)
        self.viewport_3d.camera.look_at(target)

        events.publish(ViewportRefreshEvent(source="goto_entity", refresh_2d=False))

        self.statusBar().showMessage(f"Camera moved to {entity.classname}", 2000)

    def _on_create_entity_requested(self, classname: str, position: tuple) -> None:
        """Handle entity creation request from 2D viewport context menu."""
        new_entity = create_entity(
            classname=classname,
            properties={
                "origin": f"{position[0]:.0f} {position[1]:.0f} {position[2]:.0f}",
            },
        )

        self.document.add_entity(new_entity)
        entity_idx = len(self.document.entities) - 1

        self.info_panel.update_statistics()
        self.entity_properties.update_tree()

        events.publish(EntityCreatedEvent(entity_index=entity_idx))
        events.publish(ViewportRefreshEvent(source="create_entity"))

        self.document.selection.clear()
        self.document.selection.select_entity(entity_idx)

        self.statusBar().showMessage(f"Created {classname} at ({position[0]:.0f}, {position[1]:.0f}, {position[2]:.0f})", 3000)
        self.log_message(f"Created {classname}")

    # =========================================================================
    # Controller Helper Methods
    # =========================================================================

    def get_grid_size(self) -> int:
        """Get current grid size (used by controllers)."""
        if self.viewport_2d is not None:
            return self.viewport_2d.grid_size
        return 8

    def set_document(self, new_document: MapDocument) -> None:
        """Set a new document (used by FileController)."""
        self.document = new_document

        self._refresh_viewports()

        self.info_panel.set_document(self.document)
        self.entity_properties.set_document(self.document)

        current_filters = self.filter_panel.get_filters()
        events.publish(FilterChangedEvent(filters=current_filters))

        self._update_title()

    def _init_texture_browser(self) -> None:
        """Initialize the texture browser with settings from preferences."""
        texture_path = self._settings.value("paths/texturePath", "", type=str)
        if texture_path:
            manager = get_texture_manager()
            manager.set_texture_path(texture_path)
            self.texture_browser.refresh()
            self.log_message(f"Texture path: {texture_path}")

    def _on_texture_applied(self, texture_name: str) -> None:
        """Handle texture application from the texture browser."""
        selected = self.document.selection.selected_brushes
        if not selected:
            self.statusBar().showMessage("No brushes selected", 2000)
            return

        plane_count = 0
        for entity_idx, brush_idx in selected:
            if entity_idx < len(self.document.entities):
                entity = self.document.entities[entity_idx]
                if brush_idx < len(entity.brushes):
                    brush = entity.brushes[brush_idx]
                    for plane in brush.planes:
                        plane.shader = texture_name
                        plane_count += 1

        if plane_count > 0:
            self.document.modified = True

            self.texture_properties.update_from_selection()

            events.publish(ViewportRefreshEvent(source="texture_applied"))

            self.statusBar().showMessage(
                f"Applied '{texture_name}' to {plane_count} faces", 2000
            )
            self.log_message(f"Applied texture: {texture_name}")
        else:
            self.statusBar().showMessage("No faces to apply texture to", 2000)

    def show_texture_browser(self) -> None:
        """Show and focus the texture browser dock."""
        self._texture_browser_dock.show()
        self._texture_browser_dock.raise_()
