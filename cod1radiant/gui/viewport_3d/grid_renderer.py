"""Grid and axis rendering for 3D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class GridRenderer:
    """Handles grid and axis line rendering for the 3D viewport."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

        # Grid geometry
        self.grid_vao: moderngl.VertexArray | None = None
        self.grid_vbo: moderngl.Buffer | None = None
        self.grid_vertex_count: int = 0

        # Axis VAOs (X, Y lines)
        self.axis_vaos: dict[str, moderngl.VertexArray] = {}
        self.axis_vbos: dict[str, moderngl.Buffer] = {}

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def grid_program(self) -> moderngl.Program | None:
        return self.viewport.grid_program

    def create_grid(self, grid_size: int = 64):
        """Create grid geometry."""
        if self.ctx is None or self.grid_program is None:
            return

        grid_extent = 4096
        step = grid_size

        lines = []

        # Grid lines along X
        for y in range(-grid_extent, grid_extent + step, step):
            lines.extend([
                -grid_extent, y, 0,
                grid_extent, y, 0
            ])

        # Grid lines along Y
        for x in range(-grid_extent, grid_extent + step, step):
            lines.extend([
                x, -grid_extent, 0,
                x, grid_extent, 0
            ])

        vertices = np.array(lines, dtype='f4')
        self.grid_vbo = self.ctx.buffer(vertices.tobytes())

        self.grid_vao = self.ctx.vertex_array(
            self.grid_program,
            [(self.grid_vbo, '3f', 'in_position')]
        )
        self.grid_vertex_count = len(lines) // 3

    def create_axis_lines(self):
        """Create colored axis lines forming a cross through the origin."""
        if self.ctx is None or self.grid_program is None:
            return

        axis_length = 4096

        # X axis (red): full cross from -X to +X (no Z component for ground plane)
        x_vertices = np.array([
            -axis_length, 0, 0,
            axis_length, 0, 0
        ], dtype='f4')

        # Y axis (green): full cross from -Y to +Y (no Z component for ground plane)
        y_vertices = np.array([
            0, -axis_length, 0,
            0, axis_length, 0
        ], dtype='f4')

        # Create VAOs for X and Y axis only (no Z axis)
        x_vbo = self.ctx.buffer(x_vertices.tobytes())
        y_vbo = self.ctx.buffer(y_vertices.tobytes())

        self.axis_vbos['x'] = x_vbo
        self.axis_vbos['y'] = y_vbo

        self.axis_vaos['x'] = self.ctx.vertex_array(
            self.grid_program, [(x_vbo, '3f', 'in_position')]
        )
        self.axis_vaos['y'] = self.ctx.vertex_array(
            self.grid_program, [(y_vbo, '3f', 'in_position')]
        )

    def render_grid(self, mvp: np.ndarray):
        """Render the grid."""
        settings = self.viewport._settings_manager
        if not settings.show_grid or self.grid_vao is None or self.grid_program is None:
            return

        self.grid_program['u_mvp'].write(mvp.tobytes())
        grid_color = settings.grid_color
        self.grid_program['u_color'].value = grid_color[:4]
        self.grid_vao.render(moderngl.LINES)

    def render_axes(self, mvp: np.ndarray):
        """Render the axis lines."""
        settings = self.viewport._settings_manager
        if not settings.show_axis or not self.axis_vaos or self.grid_program is None:
            return

        self.grid_program['u_mvp'].write(mvp.tobytes())

        # Set line width for axis lines
        self.ctx.line_width = settings.axis_thickness

        # Disable depth test to draw axis on top (prevents z-fighting)
        self.ctx.disable(moderngl.DEPTH_TEST)

        # X axis - Red (full cross)
        self.grid_program['u_color'].value = (0.8, 0.2, 0.2, 1.0)
        self.axis_vaos['x'].render(moderngl.LINES)

        # Y axis - Green (full cross)
        self.grid_program['u_color'].value = (0.2, 0.8, 0.2, 1.0)
        self.axis_vaos['y'].render(moderngl.LINES)

        # Re-enable depth test and reset line width
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.line_width = 1.0

    def release(self):
        """Release OpenGL resources."""
        if self.grid_vao is not None:
            self.grid_vao.release()
            self.grid_vao = None
        if self.grid_vbo is not None:
            self.grid_vbo.release()
            self.grid_vbo = None

        for vao in self.axis_vaos.values():
            vao.release()
        self.axis_vaos.clear()

        for vbo in self.axis_vbos.values():
            vbo.release()
        self.axis_vbos.clear()
