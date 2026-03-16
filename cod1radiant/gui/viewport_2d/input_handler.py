"""Input handling (mouse, keyboard) for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QWheelEvent, QMouseEvent, QKeyEvent, QCursor
from PyQt6.QtWidgets import QMenu

import numpy as np

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL

from ..tools import EditMode
from ...core import events, ViewportRefreshEvent, Brush, Vec3, get_brush_center


class InputHandler:
    """Handles mouse and keyboard input for 2D viewport."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

    def handle_wheel(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        v = self.viewport
        mouse_pos = event.position()
        wx, wy = v.screen_to_world(mouse_pos.x(), mouse_pos.y())

        delta = event.angleDelta().y()
        factor = 1.1 if delta > 0 else 0.9
        v.zoom *= factor
        v.zoom = max(0.01, min(100.0, v.zoom))

        new_wx, new_wy = v.screen_to_world(mouse_pos.x(), mouse_pos.y())
        v.offset_x -= new_wx - wx
        v.offset_y -= new_wy - wy

        v.update()

    def handle_mouse_press(self, event: QMouseEvent):
        """Handle mouse press."""
        v = self.viewport

        if event.button() == Qt.MouseButton.MiddleButton:
            v._panning = True
            v._last_mouse_pos = event.pos()
            v.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            v._right_click_pos = event.pos()
            v._last_mouse_pos = event.pos()
        elif event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
            shift = modifiers & Qt.KeyboardModifier.ShiftModifier

            sx, sy = event.pos().x(), event.pos().y()
            wx, wy = v.screen_to_world(sx, sy)

            # Clipping tool takes precedence when active
            if v._clipping_tool.is_active():
                v._clipping_tool.handle_click(wx, wy)
                return

            if ctrl and shift:
                v._selection_handler.handle_face_selection_click(wx, wy)
            elif ctrl:
                v._brush_creation_tool.start_creation(wx, wy)
            elif shift:
                v._selection_handler.handle_selection_click(event)
            elif v._edit_mode == EditMode.EDGE:
                handle = v._edge_tool.get_handle_at(sx, sy)
                if handle is not None:
                    v._edge_tool.start_drag(handle, wx, wy)
                elif not v.document.selection.selected_brushes:
                    v._brush_creation_tool.start_creation(wx, wy)
            else:
                handle = v._resize_tool.get_handle_at(sx, sy)
                if handle:
                    v._resize_tool.start_drag(handle, wx, wy)
                else:
                    result = v._selection_handler.get_brush_at(wx, wy)
                    if result:
                        entity_idx, brush_idx, brush = result
                        if v.document.selection.is_brush_selected(entity_idx, brush_idx):
                            v._selection_handler.start_drag(wx, wy)
                    elif not v.document.selection.selected_brushes:
                        v._brush_creation_tool.start_creation(wx, wy)

    def handle_mouse_release(self, event: QMouseEvent):
        """Handle mouse release."""
        v = self.viewport

        if event.button() == Qt.MouseButton.MiddleButton:
            v._panning = False
            v.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.RightButton:
            v._panning = False
            v.setCursor(Qt.CursorShape.ArrowCursor)
            if v._right_click_pos is not None:
                delta = event.pos() - v._right_click_pos
                if abs(delta.x()) < 5 and abs(delta.y()) < 5:
                    self._show_context_menu(event.globalPosition().toPoint())
            v._right_click_pos = None
        elif event.button() == Qt.MouseButton.LeftButton:
            if v._selection_handler._dragging:
                v._selection_handler.end_drag()
                v.setCursor(Qt.CursorShape.ArrowCursor)
                v.geometry_changed.emit()
            elif v._resize_tool.is_dragging():
                v._resize_tool.end_drag()
                v.setCursor(Qt.CursorShape.ArrowCursor)
                v._geometry_builder.mark_dirty()
                v.geometry_changed.emit()
            elif v._edge_tool.is_dragging():
                v._edge_tool.end_drag()
                v.setCursor(Qt.CursorShape.ArrowCursor)
                v._geometry_builder.mark_dirty()
                v.geometry_changed.emit()
            elif v._brush_creation_tool.is_creating():
                wx, wy = v.screen_to_world(event.pos().x(), event.pos().y())
                v._brush_creation_tool.finish_creation(wx, wy)
                v._edit_mode = EditMode.RESIZE
                v.setCursor(Qt.CursorShape.ArrowCursor)
                v._geometry_builder.mark_dirty()
                v.geometry_changed.emit()

    def handle_mouse_move(self, event: QMouseEvent):
        """Handle mouse move."""
        v = self.viewport
        sx, sy = event.pos().x(), event.pos().y()
        wx, wy = v.screen_to_world(sx, sy)

        # Start panning if right-click and moved enough
        if v._right_click_pos is not None and not v._panning:
            delta = event.pos() - v._right_click_pos
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                v._panning = True
                v.setCursor(Qt.CursorShape.ClosedHandCursor)

        if v._panning:
            delta = event.pos() - v._last_mouse_pos
            v.offset_x -= delta.x() / v.zoom
            v.offset_y += delta.y() / v.zoom
            v._last_mouse_pos = event.pos()
            v.update()
        elif v._clipping_tool.is_active():
            v._clipping_tool.handle_mouse_move(wx, wy)
        elif v._selection_handler._dragging:
            v._selection_handler.update_drag(wx, wy)
        elif v._resize_tool.is_dragging():
            v._resize_tool.update_drag(wx, wy)
            v._geometry_builder.mark_dirty()
        elif v._edge_tool.is_dragging():
            v._edge_tool.update_drag(wx, wy)
            v._geometry_builder.mark_dirty()
        elif v._brush_creation_tool.is_creating():
            v._brush_creation_tool.update_preview(wx, wy)
        else:
            if v._edit_mode == EditMode.EDGE:
                handle = v._edge_tool.get_handle_at(sx, sy)
                if handle is not None:
                    v.setCursor(Qt.CursorShape.SizeAllCursor)
                else:
                    v.setCursor(Qt.CursorShape.ArrowCursor)
            else:
                handle = v._resize_tool.get_handle_at(sx, sy)
                if handle:
                    v.setCursor(v._resize_tool.get_cursor_for_handle(handle))
                else:
                    v.setCursor(Qt.CursorShape.ArrowCursor)

            self._update_position_display(wx, wy)

    def _update_position_display(self, wx: float, wy: float):
        """Update the position display in status bar."""
        v = self.viewport
        axis_h, axis_v = v._get_axes()
        pos = [0, 0, 0]
        pos[axis_h] = wx
        pos[axis_v] = wy

        parent = v.parent()
        while parent:
            if hasattr(parent, 'position_label'):
                parent.position_label.setText(f"X: {pos[0]:.0f}  Y: {pos[1]:.0f}  Z: {pos[2]:.0f}")
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle key press events. Returns True if event was handled."""
        v = self.viewport
        modifiers = event.modifiers()
        shift = modifiers & Qt.KeyboardModifier.ShiftModifier

        print(f"[KEY] keyPressEvent: key={event.key()}, clip_active={v._clipping_tool.is_active()}")

        # Clipping tool keyboard shortcuts
        if v._clipping_tool.is_active():
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                print("[KEY] Enter/Return pressed in clip mode")
                if shift:
                    v._clipping_tool.confirm_clip(keep_both=True)
                else:
                    v._clipping_tool.confirm_clip(keep_both=False)
                return True
            elif event.key() == Qt.Key.Key_Tab:
                print("[KEY] Tab pressed in clip mode")
                v._clipping_tool.toggle_clip_side()
                return True
            elif event.key() == Qt.Key.Key_Escape or event.key() == Qt.Key.Key_X:
                print("[KEY] ESC/X pressed in clip mode - deactivating")
                v._clipping_tool.deactivate()
                self._show_status("Clipping cancelled")
                return True

        if event.key() == Qt.Key.Key_X:
            if v.document.selection.selected_brushes:
                v._clipping_tool.activate()
            else:
                self._show_status("Select brushes to clip first")
            return True
        elif event.key() == Qt.Key.Key_E:
            if v.document.selection.selected_brushes:
                if v._edit_mode == EditMode.EDGE:
                    v._edit_mode = EditMode.RESIZE
                    self._show_status("Resize Mode")
                else:
                    v._edit_mode = EditMode.EDGE
                    self._show_status("Edge Edit Mode")
                v.update()
            return True
        elif event.key() == Qt.Key.Key_Escape:
            v.document.selection.clear(source="viewport_2d")
            v._edit_mode = EditMode.RESIZE
            v._edge_tool.on_selection_changed()
            self._show_status("Deselected")
            v.update()
            return True
        elif event.key() == Qt.Key.Key_Space:
            self._duplicate_and_start_drag()
            return True

        return False

    def handle_tab_key(self) -> bool:
        """Handle Tab key for clip mode. Returns True if handled."""
        v = self.viewport
        if v._clipping_tool.is_active():
            print("[EVENT] Intercepting Tab for clip mode")
            v._clipping_tool.toggle_clip_side()
            return True
        return False

    def _show_status(self, message: str, timeout: int = 2000):
        """Show a status message in the main window."""
        v = self.viewport
        parent = v.parent()
        while parent:
            if hasattr(parent, 'statusBar'):
                parent.statusBar().showMessage(message, timeout)
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _show_context_menu(self, global_pos: QPoint):
        """Show context menu at the given global position."""
        v = self.viewport
        menu = QMenu(v)

        local_pos = v.mapFromGlobal(global_pos)
        wx, wy = v.screen_to_world(local_pos.x(), local_pos.y())
        world_pos = self._get_3d_position(wx, wy)

        selected = v.document.selection.selected_brushes
        has_selection = len(selected) > 0

        if has_selection:
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(self._delete_selected_brushes)

            duplicate_action = menu.addAction("Duplicate")
            duplicate_action.triggered.connect(self._duplicate_selected_brushes)

            menu.addSeparator()

            if v._edit_mode == EditMode.EDGE:
                resize_action = menu.addAction("Resize Mode")
                resize_action.triggered.connect(lambda: self._set_edit_mode(EditMode.RESIZE))
            else:
                edge_action = menu.addAction("Edge Edit Mode")
                edge_action.triggered.connect(lambda: self._set_edit_mode(EditMode.EDGE))

            menu.addSeparator()

        self._add_entity_menu(menu, world_pos)

        menu.addSeparator()

        view_menu = menu.addMenu("View")
        view_menu.addAction("Top (XY)").triggered.connect(lambda: v.set_axis('xy'))
        view_menu.addAction("Front (XZ)").triggered.connect(lambda: v.set_axis('xz'))
        view_menu.addAction("Side (YZ)").triggered.connect(lambda: v.set_axis('yz'))

        menu.addSeparator()

        if has_selection:
            center_action = menu.addAction("Center on Selection")
            center_action.triggered.connect(v.center_on_selection)

        fit_action = menu.addAction("Fit to Map")
        fit_action.triggered.connect(v.fit_to_map)

        center_origin_action = menu.addAction("Center on Origin")
        center_origin_action.triggered.connect(v.center_on_origin)

        menu.addSeparator()

        grid_menu = menu.addMenu("Grid Size")
        for size in [1, 2, 4, 8, 16, 32, 64, 128]:
            action = grid_menu.addAction(f"{size}")
            action.setCheckable(True)
            action.setChecked(v.grid_size == size)
            action.triggered.connect(lambda checked, s=size: v.set_grid_size(s))

        toggle_grid = menu.addAction("Show Grid")
        toggle_grid.setCheckable(True)
        toggle_grid.setChecked(v._show_grid)
        toggle_grid.triggered.connect(self._toggle_grid)

        menu.exec(global_pos)

    def _get_3d_position(self, wx: float, wy: float) -> tuple[float, float, float]:
        """Convert 2D viewport coordinates to 3D world position."""
        v = self.viewport
        wx = round(wx / v.grid_size) * v.grid_size
        wy = round(wy / v.grid_size) * v.grid_size

        if v.axis == 'xy':
            return (wx, wy, 0.0)
        elif v.axis == 'xz':
            return (wx, 0.0, wy)
        else:
            return (0.0, wx, wy)

    def _add_entity_menu(self, parent_menu: QMenu, world_pos: tuple[float, float, float]):
        """Add entity creation submenus to context menu."""
        from ...core import ENTITY_DEFINITIONS

        v = self.viewport

        categories = {
            "actor": [], "ammo": [], "corona": [], "func": [], "info": [],
            "item": [], "light": [], "misc": [], "mp": [], "mpweapon": [],
            "node": [], "props": [], "script": [], "trigger": [], "weapon": [],
            "worldspawn": [],
        }

        for classname in sorted(ENTITY_DEFINITIONS.keys()):
            entity_def = ENTITY_DEFINITIONS[classname]

            if not entity_def.is_point_entity:
                if classname not in ("func_group", "script_brushmodel"):
                    continue

            categorized = False
            for prefix in sorted(categories.keys(), key=len, reverse=True):
                if classname.startswith(prefix):
                    categories[prefix].append(classname)
                    categorized = True
                    break

            if not categorized:
                categories["misc"].append(classname)

        for category in sorted(categories.keys()):
            entities = categories[category]
            if not entities:
                continue

            cat_menu = parent_menu.addMenu(category)

            for classname in sorted(entities):
                if classname.startswith(category + "_"):
                    display_name = classname[len(category) + 1:]
                elif classname == category:
                    display_name = classname
                else:
                    display_name = classname

                action = cat_menu.addAction(display_name)
                action.triggered.connect(
                    lambda checked, cn=classname, pos=world_pos: v.create_entity_requested.emit(cn, pos)
                )

    def _delete_selected_brushes(self):
        """Delete all selected brushes."""
        vp = self.viewport
        selected = list(vp.document.selection.selected_brushes)
        if not selected:
            return

        for entity_idx, brush_idx in selected:
            vp._geometry_builder.remove_brush(entity_idx, brush_idx)
            vp.document.remove_brush(entity_idx, brush_idx)

        vp.document.selection.clear(source="viewport_2d")
        vp._geometry_builder.mark_dirty()
        vp.update()
        events.publish(ViewportRefreshEvent(source="viewport_2d_delete", rebuild_geometry=True))
        self._show_status(f"Deleted {len(selected)} brush(es)")

    def _duplicate_selected_brushes(self):
        """Duplicate all selected brushes."""
        vp = self.viewport
        selected = list(vp.document.selection.selected_brushes)
        if not selected:
            return

        new_keys = []
        for entity_idx, brush_idx in selected:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush and brush.is_regular:
                new_brush = brush.copy()
                new_brush.translate(Vec3(vp.grid_size, vp.grid_size, 0))
                result = vp.document.add_brush_to_worldspawn(new_brush)
                if result:
                    new_keys.append(result)

        vp.document.selection.clear(source="viewport_2d")
        for entity_idx, brush_idx in new_keys:
            vp.document.selection.select_brush(entity_idx, brush_idx, source="viewport_2d")

        vp._geometry_builder.mark_dirty()
        vp.update()
        vp._notify_3d_viewport()
        self._show_status(f"Duplicated {len(new_keys)} brush(es)")

    def _duplicate_and_start_drag(self):
        """Duplicate selected brushes and immediately start dragging them."""
        vp = self.viewport
        selected = list(vp.document.selection.selected_brushes)
        if not selected:
            return

        new_keys = []
        for entity_idx, brush_idx in selected:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush and brush.is_regular:
                new_brush = brush.copy()
                result = vp.document.add_brush_to_worldspawn(new_brush)
                if result:
                    new_keys.append(result)

        if not new_keys:
            return

        vp.document.selection.clear(source="viewport_2d")
        for entity_idx, brush_idx in new_keys:
            vp.document.selection.select_brush(entity_idx, brush_idx, source="viewport_2d")

        mouse_pos = vp.mapFromGlobal(QCursor.pos())
        wx, wy = vp.screen_to_world(mouse_pos.x(), mouse_pos.y())

        vp._selection_handler._dragging = True
        vp._selection_handler._drag_start_world = (wx, wy)
        vp._selection_handler._drag_start_positions = {}
        for entity_idx, brush_idx in new_keys:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush:
                center = get_brush_center(brush)
                if center:
                    vp._selection_handler._drag_start_positions[(entity_idx, brush_idx)] = center

        vp.setCursor(Qt.CursorShape.SizeAllCursor)
        vp._geometry_builder.mark_dirty()
        vp.update()
        vp._notify_3d_viewport()
        self._show_status(f"Duplicating {len(new_keys)} brush(es) - move mouse to position")

    def _set_edit_mode(self, mode: EditMode):
        """Set the edit mode."""
        v = self.viewport
        v._edit_mode = mode
        self._show_status(f"{'Edge Edit' if mode == EditMode.EDGE else 'Resize'} Mode")
        v.update()

    def _toggle_grid(self, checked: bool):
        """Toggle grid visibility."""
        v = self.viewport
        v._show_grid = checked
        v._settings.setValue("viewport/showGrid", checked)
        v.update()
