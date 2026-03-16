"""Selection and drag handling for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent

import numpy as np

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL

from ..tools import EditMode
from ...core import (
    Brush, ui_state, get_brush_bounds, compute_brush_vertices, Vec3,
)


class SelectionHandler:
    """Handles selection and dragging for 2D viewport."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

        # Drag state
        self._dragging = False
        self._drag_start_world: tuple[float, float] | None = None
        # Changed to use (entity_idx, brush_idx) tuples as keys
        self._drag_start_positions: dict[tuple[int, int], Vec3] | None = None

    def handle_selection_click(self, event: QMouseEvent):
        """Handle Shift+click for brush selection."""
        vp = self.viewport
        wx, wy = vp.screen_to_world(event.pos().x(), event.pos().y())
        result = self.get_brush_at(wx, wy)

        if result is not None:
            entity_idx, brush_idx, brush = result
            vp.document.selection.toggle_brush(entity_idx, brush_idx, source="viewport_2d")
            vp._edit_mode = EditMode.RESIZE
            is_selected = vp.document.selection.is_brush_selected(entity_idx, brush_idx)
            print(f"[2D Selection] Toggled brush ({entity_idx},{brush_idx}), selected: {is_selected}")
            vp.update()

    def handle_face_selection_click(self, wx: float, wy: float):
        """Handle Ctrl+Shift+click for face selection in 2D viewport."""
        vp = self.viewport
        axis_h, axis_v = vp._get_axes()

        has_filters = bool(vp._filters)
        visible_brushes = vp._filtered_brushes if has_filters else None

        clicked_entity_idx = None
        clicked_brush_idx = None
        clicked_face_idx = None

        for entity_idx, brush_idx, brush in vp.document.iter_brushes():
            key = (entity_idx, brush_idx)

            if ui_state.is_brush_hidden(entity_idx, brush_idx):
                continue

            if visible_brushes is not None and key not in visible_brushes:
                continue

            if vp.document.selection.is_brush_selected(entity_idx, brush_idx):
                continue

            # Get computed vertices
            face_vertices = vp.document.get_brush_vertices(entity_idx, brush_idx)

            for face_idx, verts in face_vertices.items():
                if len(verts) < 3:
                    continue

                points_2d = [([v.x, v.y, v.z][axis_h], [v.x, v.y, v.z][axis_v]) for v in verts]
                if self._point_in_polygon_2d(wx, wy, points_2d):
                    clicked_entity_idx = entity_idx
                    clicked_brush_idx = brush_idx
                    clicked_face_idx = face_idx
                    break

            if clicked_face_idx is not None:
                break

        if clicked_entity_idx is not None and clicked_brush_idx is not None and clicked_face_idx is not None:
            key = (clicked_entity_idx, clicked_brush_idx)

            if vp.document.selection.is_face_selected(clicked_entity_idx, clicked_brush_idx, clicked_face_idx):
                vp.document.selection.deselect_face(clicked_entity_idx, clicked_brush_idx, clicked_face_idx)
                print(f"[Face Selection 2D] Deselected face {clicked_face_idx} on brush {key}")
            else:
                vp.document.selection.select_face(clicked_entity_idx, clicked_brush_idx, clicked_face_idx, source="viewport_2d")
                print(f"[Face Selection 2D] Selected face {clicked_face_idx} on brush {key}")

            vp.update()

    def get_brush_at(self, wx: float, wy: float) -> tuple[int, int, Brush] | None:
        """Get brush or patch at world coordinates.

        Returns:
            (entity_idx, brush_idx, brush) or None if nothing found
        """
        vp = self.viewport
        axis_h, axis_v = vp._get_axes()

        has_filters = bool(vp._filters)
        visible_brushes = vp._filtered_brushes if has_filters else None

        for entity_idx, brush_idx, brush in vp.document.iter_all_geometry():
            key = (entity_idx, brush_idx)

            if ui_state.is_brush_hidden(entity_idx, brush_idx):
                continue

            if visible_brushes is not None and key not in visible_brushes:
                continue

            if brush.is_regular:
                # Get computed vertices
                face_vertices = vp.document.get_brush_vertices(entity_idx, brush_idx)

                for face_idx, verts in face_vertices.items():
                    if len(verts) < 3:
                        continue

                    points_2d = [([v.x, v.y, v.z][axis_h], [v.x, v.y, v.z][axis_v]) for v in verts]
                    if self._point_in_polygon_2d(wx, wy, points_2d):
                        return (entity_idx, brush_idx, brush)

            elif brush.is_patch:
                bounds = get_brush_bounds(brush)
                if bounds:
                    b_min, b_max = bounds
                    b_min_arr = (b_min.x, b_min.y, b_min.z)
                    b_max_arr = (b_max.x, b_max.y, b_max.z)
                    if (b_min_arr[axis_h] <= wx <= b_max_arr[axis_h] and
                        b_min_arr[axis_v] <= wy <= b_max_arr[axis_v]):
                        return (entity_idx, brush_idx, brush)

        return None

    def _point_in_polygon_2d(self, px: float, py: float, polygon: list[tuple[float, float]]) -> bool:
        """Check if a point is inside a 2D polygon using ray casting."""
        n = len(polygon)
        if n < 3:
            return False

        inside = False
        j = n - 1

        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def start_drag(self, wx: float, wy: float):
        """Start dragging selected brushes."""
        from ...core import get_brush_center

        vp = self.viewport
        self._dragging = True
        self._drag_start_world = (wx, wy)
        self._drag_start_positions = {}

        for entity_idx, brush_idx in vp.document.selection.selected_brushes:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush:
                center = get_brush_center(brush)
                if center:
                    self._drag_start_positions[(entity_idx, brush_idx)] = center

        vp.setCursor(Qt.CursorShape.SizeAllCursor)

    def update_drag(self, wx: float, wy: float):
        """Update brush positions during drag."""
        from ...core import get_brush_center

        vp = self.viewport
        if not self._drag_start_world or not self._drag_start_positions:
            return

        axis_h, axis_v = vp._get_axes()

        start_wx, start_wy = self._drag_start_world
        delta_h = wx - start_wx
        delta_v = wy - start_wy

        delta_h = round(delta_h / vp.grid_size) * vp.grid_size
        delta_v = round(delta_v / vp.grid_size) * vp.grid_size

        offset = Vec3(0.0, 0.0, 0.0)
        if axis_h == 0:
            offset = Vec3(delta_h, offset.y, offset.z)
        elif axis_h == 1:
            offset = Vec3(offset.x, delta_h, offset.z)
        else:
            offset = Vec3(offset.x, offset.y, delta_h)

        if axis_v == 0:
            offset = Vec3(delta_v, offset.y, offset.z)
        elif axis_v == 1:
            offset = Vec3(offset.x, delta_v, offset.z)
        else:
            offset = Vec3(offset.x, offset.y, delta_v)

        for entity_idx, brush_idx in vp.document.selection.selected_brushes:
            key = (entity_idx, brush_idx)
            if key in self._drag_start_positions:
                brush = vp.document.get_brush(entity_idx, brush_idx)
                if brush is None:
                    continue

                original_center = self._drag_start_positions[key]
                current_center = get_brush_center(brush)
                if current_center is None:
                    continue

                target_center = Vec3(
                    original_center.x + offset.x,
                    original_center.y + offset.y,
                    original_center.z + offset.z
                )
                move_offset = Vec3(
                    target_center.x - current_center.x,
                    target_center.y - current_center.y,
                    target_center.z - current_center.z
                )
                brush.translate(move_offset)
                vp.document.invalidate_brush_cache(entity_idx, brush_idx)

        vp._geometry_builder.mark_dirty()
        vp.update()
        vp._notify_3d_viewport()

    def end_drag(self):
        """End dragging."""
        vp = self.viewport
        self._dragging = False
        self._drag_start_world = None
        self._drag_start_positions = None
        vp._rebuild_3d_geometry()
