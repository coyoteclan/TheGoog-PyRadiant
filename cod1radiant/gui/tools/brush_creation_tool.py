"""Brush creation tool for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont

from .base_tool import BaseTool
from ...core import create_block, Vec3

if TYPE_CHECKING:
    from ..viewport_2d import Viewport2DGL


class BrushCreationTool(BaseTool):
    """Tool for creating new brushes by dragging rectangles."""

    def __init__(self, viewport: "Viewport2DGL"):
        super().__init__(viewport)

        # Creation state
        self._creating = False
        self._start_world: tuple[float, float] | None = None
        self._end_world: tuple[float, float] | None = None
        self._default_depth = 64

    def is_dragging(self) -> bool:
        return self._creating

    def is_creating(self) -> bool:
        """Alias for is_dragging - more semantic for this tool."""
        return self._creating

    def start_creation(self, wx: float, wy: float) -> None:
        """Start creating a new brush."""
        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        self._creating = True
        self._start_world = (wx, wy)
        self._end_world = (wx, wy)
        self.viewport.setCursor(Qt.CursorShape.CrossCursor)

    def update_preview(self, wx: float, wy: float) -> None:
        """Update the brush preview rectangle."""
        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        self._end_world = (wx, wy)
        self.viewport.update()

    def finish_creation(self, wx: float, wy: float) -> None:
        """Finish creating the brush."""
        wx = self.snap_to_grid(wx)
        wy = self.snap_to_grid(wy)

        self._end_world = (wx, wy)

        if self._start_world:
            start_h, start_v = self._start_world
            end_h, end_v = wx, wy

            # Check for minimum size
            if abs(end_h - start_h) >= self.grid_size and abs(end_v - start_v) >= self.grid_size:
                self._create_brush(start_h, start_v, end_h, end_v)

        # Reset state
        self._creating = False
        self._start_world = None
        self._end_world = None
        self.viewport.update()

    def _create_brush(self, x1: float, y1: float, x2: float, y2: float) -> None:
        """Create a brush from a 2D rectangle."""
        axis_h, axis_v = self._get_axes()

        # Build 3D min/max points
        min_pt = [0.0, 0.0, 0.0]
        max_pt = [0.0, 0.0, 0.0]

        min_pt[axis_h] = min(x1, x2)
        max_pt[axis_h] = max(x1, x2)
        min_pt[axis_v] = min(y1, y2)
        max_pt[axis_v] = max(y1, y2)

        # Set the third axis (depth)
        third_axis = 3 - axis_h - axis_v
        min_pt[third_axis] = 0
        max_pt[third_axis] = self._default_depth

        # Create the brush using the new create_block primitive
        brush = create_block(
            Vec3(min_pt[0], min_pt[1], min_pt[2]),
            Vec3(max_pt[0], max_pt[1], max_pt[2])
        )

        # Add to document - returns (entity_idx, brush_idx) tuple
        result = self.document.add_brush_to_worldspawn(brush)
        if result is None:
            self._show_status("Failed to create brush - no worldspawn")
            return

        entity_idx, brush_idx = result

        # Select the new brush
        self.document.selection.clear_brushes(source="brush_creation")
        self.document.selection.select_brush(entity_idx, brush_idx, source="brush_creation")

        # Update viewports (both 2D and 3D)
        self._rebuild_all_geometry()

        # Emit geometry_changed to trigger filter updates
        self.viewport.geometry_changed.emit()

        self._show_status(f"Created brush ({entity_idx}, {brush_idx})")

    def draw(self, painter: QPainter) -> None:
        """Draw the brush creation preview rectangle."""
        if not self._creating or not self._start_world or not self._end_world:
            return

        x1, y1 = self._start_world
        x2, y2 = self._end_world

        # Convert to screen coordinates
        p1 = self.world_to_screen(x1, y1)
        p2 = self.world_to_screen(x2, y2)

        # Draw rectangle outline
        pen = QPen(QColor(0, 255, 0), 2, Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(0, 255, 0, 30)))

        rect = QRectF(p1, p2).normalized()
        painter.drawRect(rect)

        # Draw dimensions text
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        axis_labels = self._get_axis_labels()

        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(0, 255, 0)))

        text = f"{axis_labels[0]}: {width:.0f}  {axis_labels[1]}: {height:.0f}"
        text_rect = rect.adjusted(5, 5, -5, -5)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, text)

    def _get_axis_labels(self) -> tuple[str, str]:
        """Get the axis labels for this viewport."""
        if self.viewport.axis == 'xy':
            return ('X', 'Y')
        elif self.viewport.axis == 'xz':
            return ('X', 'Z')
        else:
            return ('Y', 'Z')

    # Required interface methods (not really used for this tool)
    def get_handle_at(self, sx: float, sy: float) -> None:
        return None

    def start_drag(self, handle: object, wx: float, wy: float) -> None:
        self.start_creation(wx, wy)

    def update_drag(self, wx: float, wy: float) -> None:
        self.update_preview(wx, wy)

    def end_drag(self) -> None:
        if self._end_world:
            self.finish_creation(self._end_world[0], self._end_world[1])
