"""Edge editing tool for 2D viewport - Redesigned implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor

from .base_tool import BaseTool
from ...core import (
    Brush, Vec3, BrushPlane,
    compute_brush_vertices, get_all_brush_vertices, is_brush_valid,
)

if TYPE_CHECKING:
    from ..viewport_2d import Viewport2DGL


# Small epsilon for floating point comparisons
EPSILON = 1e-6


@dataclass
class EdgeOperation:
    """
    Encapsulates an edge movement operation with proper geometric limits.
    Local implementation to avoid dependency on old core.
    """
    brush_index: int
    edge_v1: np.ndarray
    edge_v2: np.ndarray

    planes_with_edge: list[int] = field(default_factory=list)
    planes_with_v1_only: list[int] = field(default_factory=list)
    planes_with_v2_only: list[int] = field(default_factory=list)
    min_buffer: float = 8.0

    @property
    def edge_midpoint(self) -> np.ndarray:
        """Get the midpoint of the edge."""
        return (self.edge_v1 + self.edge_v2) / 2.0

    def calculate_movement_normal_2d(self, axis_h: int, axis_v: int) -> np.ndarray:
        """Calculate the 2D movement normal for this edge in a specific viewport."""
        edge_h = self.edge_v2[axis_h] - self.edge_v1[axis_h]
        edge_v = self.edge_v2[axis_v] - self.edge_v1[axis_v]
        edge_len_2d = (edge_h**2 + edge_v**2)**0.5

        if edge_len_2d < EPSILON:
            return np.array([0.0, 0.0, 0.0])

        normal = np.array([0.0, 0.0, 0.0])
        normal[axis_h] = -edge_v / edge_len_2d
        normal[axis_v] = edge_h / edge_len_2d
        return normal

    def is_perpendicular_to_view(self, axis_h: int, axis_v: int, threshold: float = 1.0) -> bool:
        """Check if the edge appears as a point in the given 2D view."""
        edge_h = self.edge_v2[axis_h] - self.edge_v1[axis_h]
        edge_v = self.edge_v2[axis_v] - self.edge_v1[axis_v]
        edge_len_2d = (edge_h**2 + edge_v**2)**0.5
        return edge_len_2d < threshold

    def constrain_to_normal(self, offset: np.ndarray, axis_h: int, axis_v: int) -> np.ndarray:
        """Constrain offset to move along the edge's movement normal."""
        if self.is_perpendicular_to_view(axis_h, axis_v):
            return offset

        normal = self.calculate_movement_normal_2d(axis_h, axis_v)
        if np.linalg.norm(normal) < EPSILON:
            return offset

        projection = np.dot(offset, normal)
        return normal * projection


def create_edge_operation(
    brush: Brush,
    edge_v1: np.ndarray,
    edge_v2: np.ndarray,
    tolerance: float = 0.5,
    min_buffer: float = 8.0
) -> EdgeOperation:
    """
    Create an EdgeOperation for moving the specified edge.

    Args:
        brush: The brush containing the edge
        edge_v1: First vertex of the edge
        edge_v2: Second vertex of the edge
        tolerance: Tolerance for vertex matching
        min_buffer: Minimum distance to maintain from fixed geometry

    Returns:
        EdgeOperation with all necessary data for edge movement
    """
    # Get computed face vertices
    face_vertices = compute_brush_vertices(brush)

    planes_with_edge = []
    planes_with_v1_only = []
    planes_with_v2_only = []

    for plane_idx, vertices in face_vertices.items():
        has_v1 = False
        has_v2 = False

        for v in vertices:
            v_arr = np.array([v.x, v.y, v.z])
            if np.linalg.norm(v_arr - edge_v1) < tolerance:
                has_v1 = True
            if np.linalg.norm(v_arr - edge_v2) < tolerance:
                has_v2 = True

        if has_v1 and has_v2:
            planes_with_edge.append(plane_idx)
        elif has_v1:
            planes_with_v1_only.append(plane_idx)
        elif has_v2:
            planes_with_v2_only.append(plane_idx)

    return EdgeOperation(
        brush_index=brush.index,
        edge_v1=edge_v1.copy(),
        edge_v2=edge_v2.copy(),
        planes_with_edge=planes_with_edge,
        planes_with_v1_only=planes_with_v1_only,
        planes_with_v2_only=planes_with_v2_only,
        min_buffer=min_buffer
    )


def move_edge_with_operation(brush: Brush, operation: EdgeOperation, offset: np.ndarray) -> None:
    """
    Move an edge using a pre-computed EdgeOperation.

    Args:
        brush: The brush to modify
        operation: EdgeOperation from create_edge_operation()
        offset: 3D offset to move the edge by
    """
    offset_vec3 = Vec3(offset[0], offset[1], offset[2])
    tolerance = 0.5

    # Move plane points for planes that contain the edge
    for plane_idx in operation.planes_with_edge:
        if plane_idx >= len(brush.planes):
            continue
        plane = brush.planes[plane_idx]
        # Move points that match the edge vertices
        for attr in ['point1', 'point2', 'point3']:
            pt = getattr(plane, attr)
            pt_arr = np.array([pt.x, pt.y, pt.z])
            if (np.linalg.norm(pt_arr - operation.edge_v1) < tolerance or
                np.linalg.norm(pt_arr - operation.edge_v2) < tolerance):
                setattr(plane, attr, pt + offset_vec3)

    # Move plane points for planes with only v1
    for plane_idx in operation.planes_with_v1_only:
        if plane_idx >= len(brush.planes):
            continue
        plane = brush.planes[plane_idx]
        for attr in ['point1', 'point2', 'point3']:
            pt = getattr(plane, attr)
            pt_arr = np.array([pt.x, pt.y, pt.z])
            if np.linalg.norm(pt_arr - operation.edge_v1) < tolerance:
                setattr(plane, attr, pt + offset_vec3)

    # Move plane points for planes with only v2
    for plane_idx in operation.planes_with_v2_only:
        if plane_idx >= len(brush.planes):
            continue
        plane = brush.planes[plane_idx]
        for attr in ['point1', 'point2', 'point3']:
            pt = getattr(plane, attr)
            pt_arr = np.array([pt.x, pt.y, pt.z])
            if np.linalg.norm(pt_arr - operation.edge_v2) < tolerance:
                setattr(plane, attr, pt + offset_vec3)


class EdgeTool(BaseTool):
    """
    Tool for editing brush edges in 2D viewport.

    This implementation allows free movement during drag, then validates
    and snaps to valid geometry on release.
    """

    def __init__(self, viewport: "Viewport2DGL"):
        super().__init__(viewport)

        # Active drag state
        self._dragging = False
        self._active_operation: EdgeOperation | None = None
        self._active_brush: "Brush | None" = None
        self._brush_backup: "Brush | None" = None
        self._drag_start_world: tuple[float, float] | None = None
        self._last_valid_offset: np.ndarray | None = None

        # Visual settings
        self._handle_size = 8

        # Cached edge handles (regenerated on selection change)
        self._cached_handles: list[dict] | None = None
        self._cached_brush_indices: set[tuple[int, int]] | None = None

    def is_dragging(self) -> bool:
        return self._dragging

    def _invalidate_handle_cache(self):
        """Invalidate the cached handles."""
        self._cached_handles = None
        self._cached_brush_indices = None

    def _get_brush_edges(self, brush: Brush) -> list[tuple[np.ndarray, np.ndarray]]:
        """
        Get all unique edges of a brush as pairs of 3D vertices.

        Returns:
            List of (v1, v2) tuples representing edges
        """
        edges = set()
        edge_list = []

        # Get computed face vertices
        face_vertices = compute_brush_vertices(brush)

        for plane_idx, verts in face_vertices.items():
            n = len(verts)
            for i in range(n):
                v1 = verts[i]
                v2 = verts[(i + 1) % n]

                # Create numpy arrays from Vec3
                v1_arr = np.array([v1.x, v1.y, v1.z])
                v2_arr = np.array([v2.x, v2.y, v2.z])

                # Create a canonical key for the edge (sorted by coordinates)
                key1 = (round(v1.x, 2), round(v1.y, 2), round(v1.z, 2))
                key2 = (round(v2.x, 2), round(v2.y, 2), round(v2.z, 2))
                edge_key = (min(key1, key2), max(key1, key2))

                if edge_key not in edges:
                    edges.add(edge_key)
                    edge_list.append((v1_arr.copy(), v2_arr.copy()))

        return edge_list

    def _get_edge_handles(self) -> list[dict]:
        """
        Get edge midpoint handles for all selected brushes.

        Returns list of handle info dicts containing:
        - 'pos_3d': 3D midpoint position
        - 'pos_2d': (h, v) 2D position in world coords
        - 'depth': Depth value for sorting
        - 'brush': Reference to the brush
        - 'edge': (v1, v2) the edge vertices
        - 'is_perpendicular': True if edge is perpendicular to view
        - 'operation': Pre-computed EdgeOperation for this edge
        """
        # Check if cache is still valid
        current_indices = self.document.selection.selected_brushes

        if self._cached_handles is not None and self._cached_brush_indices == current_indices:
            return self._cached_handles

        axis_h, axis_v = self._get_axes()
        axis_depth = 3 - axis_h - axis_v

        handles = []

        for entity_idx, brush_idx in current_indices:
            brush = self.document.get_brush(entity_idx, brush_idx)
            if brush is None or not brush.is_regular:
                continue

            edges = self._get_brush_edges(brush)

            for v1, v2 in edges:
                # Calculate edge properties in 2D
                edge_h = v2[axis_h] - v1[axis_h]
                edge_v = v2[axis_v] - v1[axis_v]
                edge_len_2d = (edge_h**2 + edge_v**2)**0.5

                # Check if edge is perpendicular to view
                is_perpendicular = edge_len_2d < 1.0

                # Calculate midpoint
                midpoint = (v1 + v2) / 2.0

                # Create EdgeOperation for this edge
                operation = create_edge_operation(
                    brush, v1, v2,
                    tolerance=0.5,
                    min_buffer=self.grid_size
                )

                handles.append({
                    'pos_3d': midpoint,
                    'pos_2d': (midpoint[axis_h], midpoint[axis_v]),
                    'depth': midpoint[axis_depth],
                    'brush': brush,
                    'brush_key': (entity_idx, brush_idx),
                    'edge': (v1.copy(), v2.copy()),
                    'is_perpendicular': is_perpendicular,
                    'operation': operation,
                })

        # Sort by depth (higher = closer to camera, drawn last)
        handles.sort(key=lambda h: -h['depth'])

        # Cache the results
        self._cached_handles = handles
        self._cached_brush_indices = current_indices

        return handles

    def draw(self, painter: QPainter) -> None:
        """Draw edge mode visuals."""
        selected_indices = self.document.selection.selected_brushes
        if not selected_indices:
            return

        axis_h, axis_v = self._get_axes()
        axis_depth = 3 - axis_h - axis_v

        selection_color = self.viewport._selection_color

        # Draw edges with different styles for front/back
        for entity_idx, brush_idx in selected_indices:
            brush = self.document.get_brush(entity_idx, brush_idx)
            if brush is None or not brush.is_regular:
                continue

            edges = self._get_brush_edges(brush)

            # Calculate median depth for front/back distinction
            all_depths = [(v1[axis_depth] + v2[axis_depth]) / 2 for v1, v2 in edges]
            median_depth = sorted(all_depths)[len(all_depths) // 2] if all_depths else 0

            for v1, v2 in edges:
                edge_depth = (v1[axis_depth] + v2[axis_depth]) / 2
                p1 = self.world_to_screen(v1[axis_h], v1[axis_v])
                p2 = self.world_to_screen(v2[axis_h], v2[axis_v])

                if edge_depth >= median_depth:
                    # Front edge - solid line
                    pen = QPen(selection_color, 1)
                    pen.setStyle(Qt.PenStyle.SolidLine)
                else:
                    # Back edge - dashed line
                    pen = QPen(selection_color.darker(150), 1)
                    pen.setDashPattern([2, 4])

                painter.setPen(pen)
                painter.drawLine(p1, p2)

        # Draw handles - all blue now (no limit-based coloring)
        handles = self._get_edge_handles()
        size = self._handle_size

        # Track drawn positions to avoid overlapping handles
        drawn_positions = set()

        for handle in handles:
            key = (round(handle['pos_2d'][0], 1), round(handle['pos_2d'][1], 1))
            if key in drawn_positions:
                continue
            drawn_positions.add(key)

            pos = self.world_to_screen(handle['pos_2d'][0], handle['pos_2d'][1])

            # Default blue color for all handles
            fill_color = QColor(0, 128, 255)

            # Highlight the currently dragged handle
            if (self._dragging and self._active_operation and
                handle.get('operation') is self._active_operation):
                fill_color = QColor(255, 255, 0)  # Yellow for active

            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(QBrush(fill_color))

            if handle['is_perpendicular']:
                # Perpendicular edges - draw as circle
                painter.drawEllipse(pos, size/2, size/2)
            else:
                # Regular edges - draw as square
                rect = QRectF(pos.x() - size/2, pos.y() - size/2, size, size)
                painter.drawRect(rect)

    def get_handle_at(self, sx: float, sy: float) -> dict | None:
        """
        Get the handle at screen coordinates.

        Args:
            sx, sy: Screen coordinates

        Returns:
            Handle dict if found, None otherwise
        """
        handles = self._get_edge_handles()
        hit_radius = self._handle_size + 2

        for handle in handles:
            pos = self.world_to_screen(handle['pos_2d'][0], handle['pos_2d'][1])
            if abs(sx - pos.x()) <= hit_radius and abs(sy - pos.y()) <= hit_radius:
                return handle

        return None

    def start_drag(self, handle: dict, wx: float, wy: float) -> None:
        """
        Start dragging an edge handle.

        Args:
            handle: The handle dict from get_handle_at()
            wx, wy: World coordinates of the click
        """
        brush = handle.get('brush')
        operation = handle.get('operation')

        if brush is None or operation is None:
            return

        self._dragging = True
        self._active_brush = brush
        self._active_operation = operation
        self._drag_start_world = (wx, wy)
        self._last_valid_offset = np.array([0.0, 0.0, 0.0])

        # Create backup of the brush for restoration
        self._brush_backup = brush.copy()

        self.viewport.setCursor(Qt.CursorShape.SizeAllCursor)

    def update_drag(self, wx: float, wy: float) -> None:
        """
        Update edge position during drag.

        Allows free movement - validation happens on release.

        Args:
            wx, wy: Current world coordinates
        """
        if not self._dragging or self._active_operation is None:
            return
        if self._active_brush is None or self._brush_backup is None:
            return
        if self._drag_start_world is None:
            return

        axis_h, axis_v = self._get_axes()

        # Snap to grid
        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        start_wx, start_wy = self._drag_start_world

        # Calculate delta from start
        delta_h = wx - start_wx
        delta_v = wy - start_wy

        # Create 3D offset
        offset = np.array([0.0, 0.0, 0.0], dtype=np.float64)
        offset[axis_h] = delta_h
        offset[axis_v] = delta_v

        # Constrain to movement normal (direction only, no distance limit)
        constrained_offset = self._active_operation.constrain_to_normal(offset, axis_h, axis_v)

        # Snap constrained offset to grid
        constrained_offset[axis_h] = self.snap_to_grid(constrained_offset[axis_h])
        constrained_offset[axis_v] = self.snap_to_grid(constrained_offset[axis_v])

        # Restore brush from backup before applying new offset
        self._restore_brush_from_backup()

        # Apply the offset (no limits)
        if np.linalg.norm(constrained_offset) > 0.001:
            move_edge_with_operation(
                self._active_brush,
                self._active_operation,
                constrained_offset
            )

            # Check if result is valid and track last valid state
            valid, _ = is_brush_valid(self._active_brush, min_face_area=1.0)
            if valid:
                self._last_valid_offset = constrained_offset.copy()

        # Invalidate handle cache since geometry changed
        self._invalidate_handle_cache()

        self.viewport.update()
        self._notify_3d_viewport()

    def _restore_brush_from_backup(self) -> None:
        """Restore the active brush geometry from backup."""
        if self._brush_backup is None or self._active_brush is None:
            return

        # Copy plane data from backup
        self._active_brush.planes = [p.copy() for p in self._brush_backup.planes]

    def end_drag(self) -> None:
        """
        End edge handle dragging.

        Validates the result and snaps to last valid position if invalid.
        """
        if not self._dragging:
            return

        if self._active_brush is not None:
            # Check if current geometry is valid
            valid, error_msg = is_brush_valid(self._active_brush, min_face_area=1.0)

            if not valid:
                # Snap to last valid position
                self._restore_brush_from_backup()

                if self._last_valid_offset is not None and self._active_operation is not None:
                    if np.linalg.norm(self._last_valid_offset) > 0.001:
                        move_edge_with_operation(
                            self._active_brush,
                            self._active_operation,
                            self._last_valid_offset
                        )

                # Show status message
                self._show_status("Invalid geometry - snapped to last valid position")
            else:
                self._show_status("Edge moved")

        self._dragging = False
        self._active_operation = None
        self._active_brush = None
        self._brush_backup = None
        self._drag_start_world = None
        self._last_valid_offset = None

        # Invalidate cache since we're done editing
        self._invalidate_handle_cache()

        self._rebuild_3d_geometry()

    def _show_status(self, message: str) -> None:
        """Show a status message in the main window's status bar."""
        try:
            main_window = self.viewport.window()
            if main_window and hasattr(main_window, 'statusBar'):
                main_window.statusBar().showMessage(message, 3000)
        except Exception:
            pass

    def cancel_drag(self) -> None:
        """Cancel the current drag operation, restoring the brush."""
        if self._dragging and self._brush_backup is not None:
            self._restore_brush_from_backup()

        self._dragging = False
        self._active_operation = None
        self._active_brush = None
        self._brush_backup = None
        self._drag_start_world = None
        self._last_valid_offset = None
        self._invalidate_handle_cache()

        self.viewport.update()
        self._notify_3d_viewport()

    def get_cursor_for_handle(self, handle: object) -> Qt.CursorShape:
        """Get the appropriate cursor for a handle."""
        return Qt.CursorShape.SizeAllCursor

    def on_selection_changed(self) -> None:
        """Called when the selection changes. Invalidates cached handles."""
        self._invalidate_handle_cache()
