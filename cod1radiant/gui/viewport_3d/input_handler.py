"""Input handling (mouse, keyboard) for 3D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent, QCursor

import numpy as np

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class InputHandler:
    """Handles mouse and keyboard input for the 3D viewport."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

        # Input state
        self._mouse_captured = False
        self._last_mouse_x = 0
        self._last_mouse_y = 0
        self._keys_pressed: set[int] = set()

        # Movement timer
        self._move_timer = QTimer(viewport)
        self._move_timer.timeout.connect(self._update_movement)
        self._move_timer.setInterval(16)  # ~60 FPS

    @property
    def mouse_captured(self) -> bool:
        return self._mouse_captured

    def handle_mouse_press(self, event: QMouseEvent):
        """Handle mouse press."""
        if event.button() == Qt.MouseButton.RightButton:
            self._mouse_captured = True
            self._last_mouse_x = event.pos().x()
            self._last_mouse_y = event.pos().y()
            self.viewport.setCursor(Qt.CursorShape.BlankCursor)
            self.viewport.setFocus()
        elif event.button() == Qt.MouseButton.LeftButton:
            modifiers = event.modifiers()
            ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
            shift = modifiers & Qt.KeyboardModifier.ShiftModifier

            x, y = event.pos().x(), event.pos().y()
            ray_origin, ray_dir = self.viewport.camera.screen_to_ray(x, y, self.viewport.width(), self.viewport.height())

            selection_handler = self.viewport._selection_handler

            if ctrl and shift:
                # Ctrl+Shift+LMB: Face selection
                selection_handler.handle_face_selection_click(ray_origin, ray_dir)
            elif shift:
                # Shift+LMB: Brush selection (toggle)
                selection_handler.handle_selection_click(event)
            else:
                # LMB without Shift: Only drag if clicking on selected brush
                brush_key, clicked_brush = selection_handler.get_brush_at_ray(ray_origin, ray_dir)
                if clicked_brush and brush_key in self.viewport.document.selection.selected_brushes:
                    selection_handler.start_drag_3d(clicked_brush, brush_key, ray_origin, ray_dir)

    def handle_mouse_release(self, event: QMouseEvent):
        """Handle mouse release."""
        selection_handler = self.viewport._selection_handler

        if event.button() == Qt.MouseButton.RightButton:
            self._mouse_captured = False
            self.viewport.setCursor(Qt.CursorShape.ArrowCursor)
        elif event.button() == Qt.MouseButton.LeftButton:
            if selection_handler.dragging:
                selection_handler.end_drag_3d()
                self.viewport.setCursor(Qt.CursorShape.ArrowCursor)

    def handle_mouse_move(self, event: QMouseEvent):
        """Handle mouse move."""
        selection_handler = self.viewport._selection_handler

        if selection_handler.dragging:
            # Update drag
            x, y = event.pos().x(), event.pos().y()
            ray_origin, ray_dir = self.viewport.camera.screen_to_ray(x, y, self.viewport.width(), self.viewport.height())
            selection_handler.update_drag_3d(ray_origin, ray_dir)
            return

        if not self._mouse_captured:
            return

        dx = event.pos().x() - self._last_mouse_x
        dy = event.pos().y() - self._last_mouse_y

        modifiers = event.modifiers()
        ctrl = modifiers & Qt.KeyboardModifier.ControlModifier
        shift = modifiers & Qt.KeyboardModifier.ShiftModifier

        camera = self.viewport.camera

        if ctrl and shift:
            # Ctrl+Shift+RMB: Free look (rotate camera - both axes)
            camera.rotate(-dx, -dy)
        elif ctrl:
            # Ctrl+RMB: Move up/down + strafe left/right
            camera.move_up(-dy * 0.01)
            camera.move_right(dx * 0.01)
        else:
            # RMB only: Move forward/backward + rotate left/right
            camera.move_forward(-dy * 0.01)
            camera.rotate(-dx, 0)

        # Reset cursor to center
        center = self.viewport.rect().center()
        self._last_mouse_x = center.x()
        self._last_mouse_y = center.y()

        QCursor.setPos(self.viewport.mapToGlobal(center))

        self.viewport.update()

    def handle_wheel(self, event: QWheelEvent):
        """Handle mouse wheel for movement speed."""
        camera = self.viewport.camera
        delta = event.angleDelta().y()
        if delta > 0:
            camera.move_speed *= 1.2
        else:
            camera.move_speed /= 1.2
        camera.move_speed = max(50, min(5000, camera.move_speed))

    def handle_key_press(self, event: QKeyEvent):
        """Handle key press."""
        self._keys_pressed.add(event.key())
        settings = self.viewport._settings_manager

        # Toggle keys
        if event.key() == Qt.Key.Key_G:
            settings.show_grid = not settings.show_grid
            self.viewport.update()
        elif event.key() == Qt.Key.Key_F:
            settings.wireframe_overlay = not settings.wireframe_overlay
            self.viewport.update()
        elif event.key() == Qt.Key.Key_Home:
            self.viewport.camera.reset()
            self.viewport.update()
        elif event.key() == Qt.Key.Key_Escape:
            # ESC: Deselect all brushes and faces
            self.viewport.document.selection.clear(source="viewport_3d")
            self.viewport._selection_handler.rebuild_selected_faces_vao()
            self.viewport.update()
        elif event.key() == Qt.Key.Key_C:
            # C: Toggle frustum culling
            settings.culling_enabled = not settings.culling_enabled
            status = "enabled" if settings.culling_enabled else "disabled"
            print(f"Frustum culling {status}")
            self.viewport.update()
        elif event.key() == Qt.Key.Key_B:
            # B: Toggle batched rendering
            settings.batching_enabled = not settings.batching_enabled
            batch_renderer = self.viewport._batch_renderer
            if batch_renderer:
                batch_renderer.set_enabled(settings.batching_enabled)
            status = "enabled" if settings.batching_enabled else "disabled"
            print(f"Batched rendering {status}")
            self.viewport.update()
        elif event.key() == Qt.Key.Key_O:
            # O: Toggle octree picking
            settings.octree_enabled = not settings.octree_enabled
            status = "enabled" if settings.octree_enabled else "disabled"
            stats = self.viewport._octree.get_stats()
            print(f"Octree picking {status} (brushes: {stats['brush_count']}, leaves: {stats['leaf_nodes']})")
        elif event.key() == Qt.Key.Key_M:
            # M: Toggle entity markers
            settings.entity_markers_enabled = not settings.entity_markers_enabled
            entity_renderer = self.viewport._entity_renderer
            if entity_renderer:
                entity_renderer.set_enabled(settings.entity_markers_enabled)
            status = "enabled" if settings.entity_markers_enabled else "disabled"
            stats = entity_renderer.get_stats() if entity_renderer else {}
            print(f"Entity markers {status} (entities: {stats.get('entity_count', 0)})")
            self.viewport.update()
        elif event.key() == Qt.Key.Key_X:
            # X: Toggle texture preview mode
            self.viewport.show_textures = not self.viewport.show_textures
            status = "enabled" if self.viewport.show_textures else "disabled"
            print(f"Texture preview {status}")
            self.viewport.update()

    def handle_key_release(self, event: QKeyEvent):
        """Handle key release."""
        self._keys_pressed.discard(event.key())

    def handle_focus_out(self, event):
        """Handle focus lost."""
        self._keys_pressed.clear()
        self._mouse_captured = False
        self.viewport.setCursor(Qt.CursorShape.ArrowCursor)
        self._move_timer.stop()

    def _update_movement(self):
        """Update camera movement based on pressed keys."""
        if not self._mouse_captured:
            return

        delta = 0.016  # Approximate frame time
        camera = self.viewport.camera

        if Qt.Key.Key_W in self._keys_pressed:
            camera.move_forward(delta)
        if Qt.Key.Key_S in self._keys_pressed:
            camera.move_forward(-delta)
        if Qt.Key.Key_A in self._keys_pressed:
            camera.move_right(-delta)
        if Qt.Key.Key_D in self._keys_pressed:
            camera.move_right(delta)
        if Qt.Key.Key_Space in self._keys_pressed:
            camera.move_up(delta)
        if Qt.Key.Key_Control in self._keys_pressed:
            camera.move_up(-delta)

        if self._keys_pressed:
            self.viewport.update()
