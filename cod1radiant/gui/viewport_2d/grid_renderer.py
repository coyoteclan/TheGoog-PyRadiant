"""Grid rendering for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL


class GridRenderer:
    """Handles grid generation and rendering for 2D viewport."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

        # Grid VAOs and VBOs
        self.grid_minor_vao: moderngl.VertexArray | None = None
        self.grid_minor_vbo: moderngl.Buffer | None = None
        self.grid_major_vao: moderngl.VertexArray | None = None
        self.grid_major_vbo: moderngl.Buffer | None = None
        self.axis_x_vao: moderngl.VertexArray | None = None
        self.axis_x_vbo: moderngl.Buffer | None = None
        self.axis_y_vao: moderngl.VertexArray | None = None
        self.axis_y_vbo: moderngl.Buffer | None = None

        # Grid vertex counts
        self.grid_minor_count: int = 0
        self.grid_major_count: int = 0

        # Cached grid parameters to detect when rebuild is needed
        self._cached_grid_zoom: float = -1.0
        self._cached_grid_offset: tuple[float, float] = (0.0, 0.0)
        self._cached_grid_size: int = -1
        self._cached_viewport_size: tuple[int, int] = (0, 0)

        self._grid_dirty = True

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def line_program(self) -> moderngl.Program | None:
        return self.viewport.line_program

    def mark_dirty(self):
        """Mark grid as needing rebuild."""
        self._grid_dirty = True

    def needs_rebuild(self) -> bool:
        """Check if grid needs to be rebuilt."""
        if self._grid_dirty:
            return True

        v = self.viewport
        w, h = v.width(), v.height()

        # Check if view parameters changed significantly
        if abs(v.zoom - self._cached_grid_zoom) > 0.001:
            return True
        if (w, h) != self._cached_viewport_size:
            return True
        if v.grid_size != self._cached_grid_size:
            return True

        # Check if we've panned enough to need new grid lines
        offset_delta_x = abs(v.offset_x - self._cached_grid_offset[0])
        offset_delta_y = abs(v.offset_y - self._cached_grid_offset[1])
        world_width = w / v.zoom
        world_height = h / v.zoom

        if offset_delta_x > world_width * 0.3 or offset_delta_y > world_height * 0.3:
            return True

        return False

    def rebuild(self):
        """Rebuild the grid VAOs based on current view parameters."""
        if self.ctx is None or self.line_program is None:
            return

        v = self.viewport
        w, h = v.width(), v.height()
        if w == 0 or h == 0:
            w, h = 800, 600  # Default size if not yet shown

        # Calculate visible world bounds using the actual/default dimensions
        cx, cy = w / 2, h / 2
        min_wx = (0 - cx) / v.zoom + v.offset_x
        min_wy = -(h - cy) / v.zoom + v.offset_y
        max_wx = (w - cx) / v.zoom + v.offset_x
        max_wy = -(0 - cy) / v.zoom + v.offset_y

        # Add margin to ensure axes are always included
        margin = max(max_wx - min_wx, max_wy - min_wy) * 0.2
        min_wx -= margin
        min_wy -= margin
        max_wx += margin
        max_wy += margin

        # Ensure origin is always included in the grid
        min_wx = min(min_wx, -200)
        min_wy = min(min_wy, -200)
        max_wx = max(max_wx, 200)
        max_wy = max(max_wy, 200)

        # Calculate grid spacings
        minor_spacing = v.grid_size
        major_spacing = minor_spacing * 8

        # Adjust spacing based on zoom to prevent too many lines
        min_pixel_spacing = 8
        while minor_spacing * v.zoom < min_pixel_spacing:
            minor_spacing *= 2
        while major_spacing * v.zoom < min_pixel_spacing * 4:
            major_spacing *= 2

        # Generate minor grid lines (excluding major grid positions)
        minor_lines = []
        start_x = int(min_wx / minor_spacing) * minor_spacing
        start_y = int(min_wy / minor_spacing) * minor_spacing

        x = start_x
        while x <= max_wx:
            if x % major_spacing != 0:
                minor_lines.extend([x, min_wy, x, max_wy])
            x += minor_spacing

        y = start_y
        while y <= max_wy:
            if y % major_spacing != 0:
                minor_lines.extend([min_wx, y, max_wx, y])
            y += minor_spacing

        # Generate major grid lines (excluding origin)
        major_lines = []
        x = int(min_wx / major_spacing) * major_spacing
        while x <= max_wx:
            if x != 0:
                major_lines.extend([x, min_wy, x, max_wy])
            x += major_spacing

        y = int(min_wy / major_spacing) * major_spacing
        while y <= max_wy:
            if y != 0:
                major_lines.extend([min_wx, y, max_wx, y])
            y += major_spacing

        # Create/update minor grid VAO
        if minor_lines:
            minor_vertices = np.array(minor_lines, dtype='f4')
            self.grid_minor_vbo = self.ctx.buffer(minor_vertices.tobytes())
            self.grid_minor_vao = self.ctx.vertex_array(
                self.line_program,
                [(self.grid_minor_vbo, '2f', 'in_position')]
            )
            self.grid_minor_count = len(minor_lines) // 2
        else:
            self.grid_minor_count = 0

        # Create/update major grid VAO
        if major_lines:
            major_vertices = np.array(major_lines, dtype='f4')
            self.grid_major_vbo = self.ctx.buffer(major_vertices.tobytes())
            self.grid_major_vao = self.ctx.vertex_array(
                self.line_program,
                [(self.grid_major_vbo, '2f', 'in_position')]
            )
            self.grid_major_count = len(major_lines) // 2
        else:
            self.grid_major_count = 0

        # Create axis lines
        self._rebuild_axis_lines(min_wx, max_wx, min_wy, max_wy)

        # Update cache
        self._cached_grid_zoom = v.zoom
        self._cached_grid_offset = (v.offset_x, v.offset_y)
        self._cached_grid_size = v.grid_size
        self._cached_viewport_size = (w, h)
        self._grid_dirty = False

    def _rebuild_axis_lines(self, min_wx: float, max_wx: float, min_wy: float, max_wy: float):
        """Rebuild the origin axis lines."""
        if self.ctx is None or self.line_program is None:
            return

        # Horizontal axis (at y=0) - this is the X-axis line
        h_axis_vertices = np.array([min_wx, 0, max_wx, 0], dtype='f4')
        self.axis_x_vbo = self.ctx.buffer(h_axis_vertices.tobytes())
        self.axis_x_vao = self.ctx.vertex_array(
            self.line_program,
            [(self.axis_x_vbo, '2f', 'in_position')]
        )

        # Vertical axis (at x=0) - this is the Y-axis line
        v_axis_vertices = np.array([0, min_wy, 0, max_wy], dtype='f4')
        self.axis_y_vbo = self.ctx.buffer(v_axis_vertices.tobytes())
        self.axis_y_vao = self.ctx.vertex_array(
            self.line_program,
            [(self.axis_y_vbo, '2f', 'in_position')]
        )

    def draw(self):
        """Draw the grid using ModernGL."""
        if self.line_program is None:
            return

        v = self.viewport

        # Draw minor grid
        if self.grid_minor_vao and self.grid_minor_count > 0:
            self.line_program['u_color'].value = v._grid_minor_color[:4]
            self.grid_minor_vao.render(moderngl.LINES)

        # Draw major grid
        if self.grid_major_vao and self.grid_major_count > 0:
            self.line_program['u_color'].value = v._grid_major_color[:4]
            self.grid_major_vao.render(moderngl.LINES)

        # Draw origin axes with correct colors
        h_label, v_label = v._get_axis_labels()

        # Increase line width for axes
        self.ctx.line_width = 2.0

        # Horizontal axis (uses horizontal axis color)
        if self.axis_x_vao:
            self.line_program['u_color'].value = self._get_axis_color_tuple(h_label)
            self.axis_x_vao.render(moderngl.LINES)

        # Vertical axis (uses vertical axis color)
        if self.axis_y_vao:
            self.line_program['u_color'].value = self._get_axis_color_tuple(v_label)
            self.axis_y_vao.render(moderngl.LINES)

        # Reset line width
        self.ctx.line_width = 1.0

    def _get_axis_color_tuple(self, axis_name: str) -> tuple:
        """Get the color tuple for an axis (X=red, Y=green, Z=blue)."""
        if axis_name == 'X':
            return (0.7, 0.24, 0.24, 1.0)
        elif axis_name == 'Y':
            return (0.24, 0.7, 0.24, 1.0)
        else:  # Z
            return (0.24, 0.24, 0.7, 1.0)
