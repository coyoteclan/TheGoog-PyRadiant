"""Resize tool for 2D viewport - handles for scaling selected brushes."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

from .base_tool import BaseTool
from ...core import get_brush_bounds, Vec3

if TYPE_CHECKING:
    from ..viewport_2d import Viewport2DGL
    from ...core import Brush


class ResizeTool(BaseTool):
    """Tool for resizing selected brushes via corner/edge handles."""

    def __init__(self, viewport: "Viewport2DGL"):
        super().__init__(viewport)

        # Resize state
        self._resizing = False
        self._resize_handle: str | None = None
        self._resize_start_bounds: tuple[np.ndarray, np.ndarray] | None = None
        self._resize_start_mouse: tuple[float, float] | None = None
        self._resize_original_brushes: dict = {}

        # Visual settings
        self._handle_size = 8

    def is_dragging(self) -> bool:
        return self._resizing

    def _get_selection_bounds(self) -> tuple[float, float, float, float] | None:
        """Get 2D bounds of selection (min_h, min_v, max_h, max_v)."""
        selected_brushes = self.document.selection.get_selected_brushes(self.document)
        if not selected_brushes:
            return None

        axis_h, axis_v = self._get_axes()

        min_h, min_v = float('inf'), float('inf')
        max_h, max_v = float('-inf'), float('-inf')

        for brush in selected_brushes:
            bounds = get_brush_bounds(brush)
            if bounds is None:
                continue
            b_min, b_max = bounds
            b_min_arr = (b_min.x, b_min.y, b_min.z)
            b_max_arr = (b_max.x, b_max.y, b_max.z)
            min_h = min(min_h, b_min_arr[axis_h])
            min_v = min(min_v, b_min_arr[axis_v])
            max_h = max(max_h, b_max_arr[axis_h])
            max_v = max(max_v, b_max_arr[axis_v])

        return (min_h, min_v, max_h, max_v)

    def _get_handles(self) -> dict[str, QPointF]:
        """Get all resize handle positions in screen coordinates."""
        bounds = self._get_selection_bounds()
        if bounds is None:
            return {}

        min_h, min_v, max_h, max_v = bounds

        top_left = self.world_to_screen(min_h, max_v)
        top_right = self.world_to_screen(max_h, max_v)
        bottom_left = self.world_to_screen(min_h, min_v)
        bottom_right = self.world_to_screen(max_h, min_v)

        return {
            'nw': top_left,
            'n': QPointF((top_left.x() + top_right.x()) / 2, top_left.y()),
            'ne': top_right,
            'e': QPointF(top_right.x(), (top_right.y() + bottom_right.y()) / 2),
            'se': bottom_right,
            's': QPointF((bottom_left.x() + bottom_right.x()) / 2, bottom_right.y()),
            'sw': bottom_left,
            'w': QPointF(top_left.x(), (top_left.y() + bottom_left.y()) / 2),
        }

    def draw(self, painter: QPainter) -> None:
        """Draw resize handles."""
        handles = self._get_handles()
        if not handles:
            return

        size = self._handle_size
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.setBrush(QBrush(self.viewport._selection_color))

        for name, pos in handles.items():
            rect = QRectF(pos.x() - size/2, pos.y() - size/2, size, size)
            painter.drawRect(rect)

    def get_handle_at(self, sx: float, sy: float) -> str | None:
        """Get the resize handle at screen coordinates."""
        handles = self._get_handles()
        hit_radius = self._handle_size

        for name, pos in handles.items():
            if abs(sx - pos.x()) <= hit_radius and abs(sy - pos.y()) <= hit_radius:
                return name

        return None

    def get_cursor_for_handle(self, handle: str) -> Qt.CursorShape:
        """Get the appropriate cursor for a resize handle."""
        cursors = {
            'nw': Qt.CursorShape.SizeFDiagCursor,
            'se': Qt.CursorShape.SizeFDiagCursor,
            'ne': Qt.CursorShape.SizeBDiagCursor,
            'sw': Qt.CursorShape.SizeBDiagCursor,
            'n': Qt.CursorShape.SizeVerCursor,
            's': Qt.CursorShape.SizeVerCursor,
            'e': Qt.CursorShape.SizeHorCursor,
            'w': Qt.CursorShape.SizeHorCursor,
        }
        return cursors.get(handle, Qt.CursorShape.ArrowCursor)

    def start_drag(self, handle: str, wx: float, wy: float) -> None:
        """Start resizing selected brushes."""
        self._resizing = True
        self._resize_handle = handle
        self._resize_start_mouse = (wx, wy)

        selected_brushes = self.document.selection.get_selected_brushes(self.document)
        if not selected_brushes:
            self._resizing = False
            return

        axis_h, axis_v = self._get_axes()

        # Calculate combined 2D bounds
        min_h, min_v = float('inf'), float('inf')
        max_h, max_v = float('-inf'), float('-inf')

        for brush in selected_brushes:
            bounds = get_brush_bounds(brush)
            if bounds is None:
                continue
            b_min, b_max = bounds
            b_min_arr = (b_min.x, b_min.y, b_min.z)
            b_max_arr = (b_max.x, b_max.y, b_max.z)
            min_h = min(min_h, b_min_arr[axis_h])
            min_v = min(min_v, b_min_arr[axis_v])
            max_h = max(max_h, b_max_arr[axis_h])
            max_v = max(max_v, b_max_arr[axis_v])

        # Store as 3D bounds
        min_3d = np.zeros(3, dtype=np.float64)
        max_3d = np.zeros(3, dtype=np.float64)
        min_3d[axis_h] = min_h
        min_3d[axis_v] = min_v
        max_3d[axis_h] = max_h
        max_3d[axis_v] = max_v

        # Get third axis bounds too
        third_axis = 3 - axis_h - axis_v
        for brush in selected_brushes:
            bounds = get_brush_bounds(brush)
            if bounds is None:
                continue
            b_min, b_max = bounds
            b_min_arr = (b_min.x, b_min.y, b_min.z)
            b_max_arr = (b_max.x, b_max.y, b_max.z)
            min_3d[third_axis] = min(min_3d[third_axis], b_min_arr[third_axis]) if min_3d[third_axis] != 0 else b_min_arr[third_axis]
            max_3d[third_axis] = max(max_3d[third_axis], b_max_arr[third_axis]) if max_3d[third_axis] != 0 else b_max_arr[third_axis]

        self._resize_start_bounds = (min_3d.copy(), max_3d.copy())

        # Store original bounds for each brush (keyed by brush.index)
        self._resize_original_brushes = {}
        for brush in selected_brushes:
            bounds = get_brush_bounds(brush)
            if bounds is None:
                continue
            b_min, b_max = bounds
            self._resize_original_brushes[brush.index] = {
                'min': np.array([b_min.x, b_min.y, b_min.z]),
                'max': np.array([b_max.x, b_max.y, b_max.z]),
            }

        self.viewport.setCursor(self.get_cursor_for_handle(handle))

    def update_drag(self, wx: float, wy: float) -> None:
        """Update brush sizes during resize.

        All selected brushes are resized on the side corresponding to the handle.
        For example, dragging the west handle moves the west side of ALL brushes.
        """
        if not self._resize_start_bounds or not self._resize_handle or not self._resize_start_mouse:
            return

        axis_h, axis_v = self._get_axes()

        # Snap to grid
        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        # Get original selection bounds
        orig_min, orig_max = self._resize_start_bounds
        handle = self._resize_handle

        # Calculate the delta movement for each edge
        delta_west = 0.0
        delta_east = 0.0
        delta_south = 0.0
        delta_north = 0.0

        if 'w' in handle:
            # West edge moves, but can't go past east edge
            new_west = min(wx, orig_max[axis_h] - self.grid_size)
            delta_west = new_west - orig_min[axis_h]
        if 'e' in handle:
            # East edge moves, but can't go past west edge
            new_east = max(wx, orig_min[axis_h] + self.grid_size)
            delta_east = new_east - orig_max[axis_h]
        if 's' in handle:
            # South edge moves, but can't go past north edge
            new_south = min(wy, orig_max[axis_v] - self.grid_size)
            delta_south = new_south - orig_min[axis_v]
        if 'n' in handle:
            # North edge moves, but can't go past south edge
            new_north = max(wy, orig_min[axis_v] + self.grid_size)
            delta_north = new_north - orig_max[axis_v]

        # Apply transformation to each brush
        for brush in self.document.selection.get_selected_brushes(self.document):
            if brush.index not in self._resize_original_brushes:
                continue

            orig_brush_data = self._resize_original_brushes[brush.index]
            brush_orig_min = orig_brush_data['min'].copy()
            brush_orig_max = orig_brush_data['max'].copy()

            # Determine new bounds for this brush
            brush_new_min = brush_orig_min.copy()
            brush_new_max = brush_orig_max.copy()

            # Move the corresponding edge for ALL brushes
            if 'w' in handle:
                brush_new_min[axis_h] = brush_orig_min[axis_h] + delta_west
            if 'e' in handle:
                brush_new_max[axis_h] = brush_orig_max[axis_h] + delta_east
            if 's' in handle:
                brush_new_min[axis_v] = brush_orig_min[axis_v] + delta_south
            if 'n' in handle:
                brush_new_max[axis_v] = brush_orig_max[axis_v] + delta_north

            # Ensure minimum size per brush
            for axis in [axis_h, axis_v]:
                if brush_new_max[axis] - brush_new_min[axis] < self.grid_size:
                    # Restore original to prevent degenerate brush
                    brush_new_min[axis] = brush_orig_min[axis]
                    brush_new_max[axis] = brush_orig_max[axis]

            # Calculate target center and size
            target_center = (brush_new_min + brush_new_max) / 2
            target_size = brush_new_max - brush_new_min

            # Get current brush state
            bounds = get_brush_bounds(brush)
            if bounds is None:
                continue
            b_min, b_max = bounds
            current_min = np.array([b_min.x, b_min.y, b_min.z])
            current_max = np.array([b_max.x, b_max.y, b_max.z])
            current_center = (current_min + current_max) / 2
            current_size = current_max - current_min

            # Calculate scale factors
            scale = np.ones(3)
            for i in range(3):
                if current_size[i] > 0.001:
                    scale[i] = target_size[i] / current_size[i]

            # Apply scale around current center (uniform scale for now)
            if not np.allclose(scale, [1, 1, 1]):
                avg_scale = (scale[0] + scale[1] + scale[2]) / 3
                brush.scale(avg_scale, Vec3(current_center[0], current_center[1], current_center[2]))

            # Move to target center
            center = brush.get_center()
            new_center = np.array([center.x, center.y, center.z])
            offset = target_center - new_center
            if np.linalg.norm(offset) > 0.001:
                brush.translate(Vec3(offset[0], offset[1], offset[2]))

        self.viewport.update()
        self._notify_3d_viewport()

    def end_drag(self) -> None:
        """End resizing."""
        self._resizing = False
        self._resize_handle = None
        self._resize_start_bounds = None
        self._resize_start_mouse = None
        self._resize_original_brushes = {}

        self._rebuild_3d_geometry()
