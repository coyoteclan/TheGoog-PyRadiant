"""Brush clipping tool for 2D viewport."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

from .base_tool import BaseTool
from ...core import (
    Brush, BrushPlane, Vec3, BrushType, TextureParams,
    get_all_brush_vertices,
)

if TYPE_CHECKING:
    from ..viewport_2d import Viewport2DGL


class ClipSide(Enum):
    """Which side of the clip plane to keep."""
    FRONT = auto()  # Keep side in direction of normal
    BACK = auto()   # Keep side opposite to normal
    BOTH = auto()   # Split into two brushes


class ClippingTool(BaseTool):
    """Tool for clipping brushes with a plane defined by two points."""

    def __init__(self, viewport: "Viewport2DGL"):
        super().__init__(viewport)

        # Clipping state
        self._active = False
        self._point1: tuple[float, float] | None = None  # First clip point (world coords)
        self._point2: tuple[float, float] | None = None  # Second clip point (world coords)
        self._point2_confirmed = False  # True when second point has been clicked (not just preview)
        self._clip_side = ClipSide.FRONT
        self._defining_points = False  # True while dragging to define clip line

        # Visual settings
        self._point_radius = 6
        self._line_color = QColor(255, 255, 0)  # Yellow clip line
        self._point_color = QColor(255, 0, 0)   # Red clip points
        self._preview_color = QColor(255, 100, 100, 80)  # Semi-transparent red for removed part

    def is_active(self) -> bool:
        """Return True if clipping mode is active."""
        return self._active

    def is_dragging(self) -> bool:
        """Return True if currently defining clip line."""
        return self._defining_points

    def activate(self) -> None:
        """Activate clipping mode."""
        if not self.document.selection.has_selection:
            self._show_status("Select brushes to clip first")
            return

        self._active = True
        self._point1 = None
        self._point2 = None
        self._point2_confirmed = False
        self._clip_side = ClipSide.FRONT
        self._show_status("CLIP MODE")
        self._log_console("[CLIP MODE] Activated")
        self._log_console("  Click to place first point, then second point")
        self._log_console("  Tab: flip keep-side | Enter: keep highlighted | Shift+Enter: keep both | X/Esc: cancel")
        self.viewport.update()

    def deactivate(self) -> None:
        """Deactivate clipping mode."""
        self._active = False
        self._point1 = None
        self._point2 = None
        self._point2_confirmed = False
        self._defining_points = False
        self.viewport.update()

    def toggle_clip_side(self) -> None:
        """Toggle which side of the clip plane to keep (Tab key). Cycles between FRONT and BACK."""
        print(f"[CLIP] toggle_clip_side called, active={self._active}")
        if not self._active:
            return

        old_side = self._clip_side
        # Only cycle between FRONT and BACK (BOTH is via Shift+Enter)
        if self._clip_side == ClipSide.FRONT:
            self._clip_side = ClipSide.BACK
        else:
            self._clip_side = ClipSide.FRONT

        print(f"[CLIP] Toggled clip side: {old_side} -> {self._clip_side}")
        self.viewport.update()

    def confirm_clip(self, keep_both: bool = False) -> bool:
        """Apply the clip to selected brushes.

        Args:
            keep_both: If True, keep both sides (split). If False, keep only the highlighted side.

        Returns True if successful.
        """
        print(f"[CLIP] confirm_clip called, keep_both={keep_both}, active={self._active}")
        print(f"[CLIP]   point1={self._point1}, point2={self._point2}, confirmed={self._point2_confirmed}")

        if not self._active or self._point1 is None or self._point2 is None:
            print("[CLIP] Early return: not active or points not set")
            return False

        if not self._point2_confirmed:
            self._show_status("Place second clip point first")
            print("[CLIP] Early return: point2 not confirmed")
            return False

        selected_brushes = self.document.selection.get_selected_brushes(self.document)
        print(f"[CLIP] Selected brushes: {len(selected_brushes)}")
        if not selected_brushes:
            self._show_status("No brushes selected")
            return False

        # Build the 3D clip plane from the 2D line
        clip_plane = self._build_clip_plane()
        print(f"[CLIP] clip_plane: {clip_plane}")
        if clip_plane is None:
            self._show_status("Invalid clip plane")
            print("[CLIP] Invalid clip plane - returning False")
            return False

        # Determine effective clip side
        effective_side = ClipSide.BOTH if keep_both else self._clip_side
        print(f"[CLIP] effective_side: {effective_side}")

        # Clip each selected brush - we need indices for removal
        new_brushes: list[Brush] = []
        indices_to_remove: list[tuple[int, int]] = []

        # Get selected brush indices
        selected_indices = list(self.document.selection.selected_brushes)

        for entity_idx, brush_idx in selected_indices:
            brush = self.document.get_brush(entity_idx, brush_idx)
            if brush is None:
                continue

            print(f"[CLIP] Processing brush ({entity_idx}, {brush_idx})")
            result = self._clip_brush(brush, clip_plane)
            print(f"[CLIP]   _clip_brush result: {result}")

            if result is None:
                # Brush is entirely on one side, keep or remove based on clip_side
                side = self._classify_brush_side(brush, clip_plane)
                print(f"[CLIP]   Brush entirely on {side} side")
                if effective_side == ClipSide.BOTH:
                    # Keep all brushes when splitting
                    pass
                elif (effective_side == ClipSide.FRONT and side == 'back') or \
                     (effective_side == ClipSide.BACK and side == 'front'):
                    indices_to_remove.append((entity_idx, brush_idx))
                    print(f"[CLIP]   -> Marking for removal")
            else:
                # Brush was clipped
                front_brush, back_brush = result
                print(f"[CLIP]   Brush clipped: front={front_brush is not None}, back={back_brush is not None}")
                indices_to_remove.append((entity_idx, brush_idx))

                if effective_side == ClipSide.FRONT and front_brush:
                    new_brushes.append(front_brush)
                    print(f"[CLIP]   -> Keeping front brush")
                elif effective_side == ClipSide.BACK and back_brush:
                    new_brushes.append(back_brush)
                    print(f"[CLIP]   -> Keeping back brush")
                elif effective_side == ClipSide.BOTH:
                    if front_brush:
                        new_brushes.append(front_brush)
                        print(f"[CLIP]   -> Keeping front brush (BOTH mode)")
                    if back_brush:
                        new_brushes.append(back_brush)
                        print(f"[CLIP]   -> Keeping back brush (BOTH mode)")

        print(f"[CLIP] Brushes to remove: {len(indices_to_remove)}, New brushes: {len(new_brushes)}")

        # Clear selection before removing brushes
        self.document.selection.clear_brushes(source="clipping")

        # Apply changes to document - remove in reverse order to preserve indices
        for entity_idx, brush_idx in sorted(indices_to_remove, reverse=True):
            print(f"[CLIP] Removing brush ({entity_idx}, {brush_idx})")
            self.document.remove_brush(entity_idx, brush_idx)

        for brush in new_brushes:
            result = self.document.add_brush_to_worldspawn(brush)
            if result:
                entity_idx, brush_idx = result
                print(f"[CLIP] Adding new brush ({entity_idx}, {brush_idx})")
                self.document.selection.select_brush(entity_idx, brush_idx, source="clipping")

        # Rebuild geometry
        self._rebuild_all_geometry()
        self.viewport.geometry_changed.emit()

        # Deactivate clipping mode
        self.deactivate()
        self._show_status(f"Clipped {len(brushes_to_remove)} brush(es)")
        return True

    def _build_clip_plane(self) -> tuple[np.ndarray, np.ndarray] | None:
        """
        Build a 3D clip plane from the 2D clip line.

        Returns (plane_point, plane_normal) or None if invalid.
        """
        if self._point1 is None or self._point2 is None:
            return None

        # Check for degenerate line
        dx = self._point2[0] - self._point1[0]
        dy = self._point2[1] - self._point1[1]
        if abs(dx) < 0.001 and abs(dy) < 0.001:
            return None

        axis_h, axis_v = self._get_axes()
        third_axis = 3 - axis_h - axis_v

        # Build 3D point on the plane
        plane_point = np.zeros(3)
        plane_point[axis_h] = self._point1[0]
        plane_point[axis_v] = self._point1[1]
        plane_point[third_axis] = 0

        # Build direction vector along the clip line (in 3D)
        line_dir = np.zeros(3)
        line_dir[axis_h] = dx
        line_dir[axis_v] = dy
        line_dir = line_dir / np.linalg.norm(line_dir)

        # Third axis direction (perpendicular to viewport)
        third_dir = np.zeros(3)
        third_dir[third_axis] = 1.0

        # Normal is perpendicular to both the line and the third axis
        plane_normal = np.cross(line_dir, third_dir)
        plane_normal = plane_normal / np.linalg.norm(plane_normal)

        return (plane_point, plane_normal)

    def _classify_brush_side(self, brush: Brush, clip_plane: tuple[np.ndarray, np.ndarray]) -> str:
        """Classify which side of the plane a brush is on."""
        plane_point, plane_normal = clip_plane

        front_count = 0
        back_count = 0

        vertices = get_all_brush_vertices(brush)
        for vertex in vertices:
            v_arr = np.array([vertex.x, vertex.y, vertex.z])
            dist = np.dot(v_arr - plane_point, plane_normal)
            if dist > 0.001:
                front_count += 1
            elif dist < -0.001:
                back_count += 1

        if front_count > 0 and back_count == 0:
            return 'front'
        elif back_count > 0 and front_count == 0:
            return 'back'
        else:
            return 'spanning'

    def _clip_brush(self, brush: Brush, clip_plane: tuple[np.ndarray, np.ndarray]) -> tuple[Brush | None, Brush | None] | None:
        """
        Clip a brush with a plane using CSG plane-clipping.

        Returns:
            (front_brush, back_brush) if brush spans the plane
            None if brush is entirely on one side
        """
        plane_point, plane_normal = clip_plane
        plane_normal = plane_normal / np.linalg.norm(plane_normal)

        # Check if brush spans the plane
        side = self._classify_brush_side(brush, clip_plane)
        if side != 'spanning':
            return None

        # Helper to create a clip plane from 3 points
        def make_clip_plane(normal_dir: np.ndarray) -> BrushPlane:
            """Create a clip plane with correct winding."""
            # Find two vectors perpendicular to the normal
            if abs(normal_dir[2]) < 0.9:
                up = np.array([0.0, 0.0, 1.0])
            else:
                up = np.array([0.0, 1.0, 0.0])

            right = np.cross(normal_dir, up)
            right = right / np.linalg.norm(right)
            forward = np.cross(right, normal_dir)
            forward = forward / np.linalg.norm(forward)

            # Create 3 points on the plane
            p1 = plane_point.copy()
            p2 = plane_point + right * 64
            p3 = plane_point + forward * 64

            return BrushPlane(
                point1=Vec3(p1[0], p1[1], p1[2]),
                point2=Vec3(p2[0], p2[1], p2[2]),
                point3=Vec3(p3[0], p3[1], p3[2]),
                shader="common/caulk",
                texture=TextureParams()
            )

        # Create FRONT brush (keeps the side in direction of arrow/normal)
        # Clip face normal points INTO the brush (opposite to plane_normal)
        front_planes = [p.copy() for p in brush.planes]
        clip_plane_front = make_clip_plane(-plane_normal)
        front_planes.append(clip_plane_front)

        front_brush = Brush(
            index=0,
            brush_type=BrushType.REGULAR,
            planes=front_planes
        )

        # Create BACK brush (keeps the side opposite to arrow/normal)
        # Clip face normal points INTO the brush (same as plane_normal)
        back_planes = [p.copy() for p in brush.planes]
        clip_plane_back = make_clip_plane(plane_normal)
        back_planes.append(clip_plane_back)

        back_brush = Brush(
            index=0,
            brush_type=BrushType.REGULAR,
            planes=back_planes
        )

        # Validate the resulting brushes
        front_verts = get_all_brush_vertices(front_brush)
        back_verts = get_all_brush_vertices(back_brush)

        front_valid = len(front_verts) >= 4
        back_valid = len(back_verts) >= 4

        # Additional check: brush must have non-zero volume
        if front_valid:
            f_min, f_max = front_brush.get_bounding_box()
            f_size = [f_max.x - f_min.x, f_max.y - f_min.y, f_max.z - f_min.z]
            if any(s < 0.1 for s in f_size):
                front_valid = False

        if back_valid:
            b_min, b_max = back_brush.get_bounding_box()
            b_size = [b_max.x - b_min.x, b_max.y - b_min.y, b_max.z - b_min.z]
            if any(s < 0.1 for s in b_size):
                back_valid = False

        print(f"[CLIP] Front brush: {len(front_verts)} verts, valid={front_valid}")
        print(f"[CLIP] Back brush: {len(back_verts)} verts, valid={back_valid}")

        # IMPORTANT: Swap front and back to match the visual preview direction
        # The visual preview shows "FRONT" as the side the arrow points TO
        # But our clip plane normal points the opposite way
        return (
            back_brush if back_valid else None,
            front_brush if front_valid else None
        )

    def handle_click(self, wx: float, wy: float) -> bool:
        """
        Handle a click in clipping mode.

        Returns True if the click was handled.
        """
        if not self._active:
            return False

        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        if self._point1 is None:
            # Set first point
            self._point1 = (wx, wy)
            self._point2_confirmed = False
        elif not self._point2_confirmed:
            # Confirm second point
            self._point2 = (wx, wy)
            self._point2_confirmed = True

        self.viewport.update()
        return True

    def handle_mouse_move(self, wx: float, wy: float) -> None:
        """Update preview during mouse movement."""
        if not self._active or self._point1 is None:
            return

        # Only update preview if second point not yet confirmed
        if self._point2_confirmed:
            return

        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        # Update second point for preview
        self._point2 = (wx, wy)
        self.viewport.update()

    def draw(self, painter: QPainter) -> None:
        """Draw the clip line and points."""
        if not self._active:
            return

        # Draw first point if set
        if self._point1 is not None:
            p1_screen = self.world_to_screen(self._point1[0], self._point1[1])
            painter.setPen(QPen(self._point_color, 2))
            painter.setBrush(QBrush(self._point_color))
            painter.drawEllipse(
                QPointF(p1_screen.x(), p1_screen.y()),
                self._point_radius, self._point_radius
            )

        # Draw second point and line if set
        if self._point1 is not None and self._point2 is not None:
            p1_screen = self.world_to_screen(self._point1[0], self._point1[1])
            p2_screen = self.world_to_screen(self._point2[0], self._point2[1])

            # Draw the clip line
            painter.setPen(QPen(self._line_color, 2))
            painter.drawLine(p1_screen, p2_screen)

            # Draw second point
            painter.setPen(QPen(self._point_color, 2))
            painter.setBrush(QBrush(self._point_color))
            painter.drawEllipse(
                QPointF(p2_screen.x(), p2_screen.y()),
                self._point_radius, self._point_radius
            )

            # Draw direction indicator (arrow showing which side is kept)
            self._draw_direction_indicator(painter, p1_screen, p2_screen)

            # Draw clip side label
            self._draw_clip_side_label(painter, p1_screen, p2_screen)

    def _draw_direction_indicator(self, painter: QPainter, p1: QPointF, p2: QPointF) -> None:
        """Draw an arrow indicating which side will be kept."""
        # Calculate perpendicular direction
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        length = np.sqrt(dx * dx + dy * dy)
        if length < 1:
            return

        # Perpendicular unit vector
        perp_x = -dy / length
        perp_y = dx / length

        # Flip direction based on clip side
        if self._clip_side == ClipSide.BACK:
            perp_x = -perp_x
            perp_y = -perp_y

        # Arrow position (center of line)
        mid_x = (p1.x() + p2.x()) / 2
        mid_y = (p1.y() + p2.y()) / 2

        # Arrow length
        arrow_len = 30

        if self._clip_side != ClipSide.BOTH:
            # Draw arrow
            end_x = mid_x + perp_x * arrow_len
            end_y = mid_y + perp_y * arrow_len

            painter.setPen(QPen(QColor(0, 255, 0), 2))
            painter.drawLine(QPointF(mid_x, mid_y), QPointF(end_x, end_y))

            # Arrowhead
            head_size = 8
            angle = np.arctan2(perp_y, perp_x)
            head1_x = end_x - head_size * np.cos(angle - 0.5)
            head1_y = end_y - head_size * np.sin(angle - 0.5)
            head2_x = end_x - head_size * np.cos(angle + 0.5)
            head2_y = end_y - head_size * np.sin(angle + 0.5)

            painter.drawLine(QPointF(end_x, end_y), QPointF(head1_x, head1_y))
            painter.drawLine(QPointF(end_x, end_y), QPointF(head2_x, head2_y))

    def _draw_clip_side_label(self, painter: QPainter, p1: QPointF, p2: QPointF) -> None:
        """Draw a label showing the current clip side mode."""
        mid_x = (p1.x() + p2.x()) / 2
        mid_y = (p1.y() + p2.y()) / 2

        labels = {
            ClipSide.FRONT: "KEEP FRONT",
            ClipSide.BACK: "KEEP BACK",
            ClipSide.BOTH: "SPLIT BOTH",
        }

        font = QFont("Arial", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(self._line_color))
        painter.drawText(QPointF(mid_x + 40, mid_y - 10), labels[self._clip_side])

    # Required interface methods
    def get_handle_at(self, sx: float, sy: float) -> None:
        return None

    def start_drag(self, handle: object, wx: float, wy: float) -> None:
        pass

    def update_drag(self, wx: float, wy: float) -> None:
        pass

    def end_drag(self) -> None:
        pass
