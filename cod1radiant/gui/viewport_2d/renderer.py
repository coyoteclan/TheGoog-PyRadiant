"""Main rendering orchestration for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL

from ...core import Brush


class Renderer:
    """Orchestrates all 2D viewport rendering."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def line_program(self) -> moderngl.Program | None:
        return self.viewport.line_program

    @property
    def point_program(self) -> moderngl.Program | None:
        return self.viewport.point_program

    def draw_brushes(self):
        """Draw all brushes and patches with content-flag-based colors."""
        vp = self.viewport
        if self.line_program is None:
            return

        # Collect selected brush keys (entity_idx, brush_idx)
        selected_keys = vp.document.selection.selected_brushes

        # Check if we have filters active
        has_filters = bool(vp._filters)
        visible_brushes = vp._filtered_brushes if has_filters else None

        # Re-bind shader program and set uniforms
        self.line_program['u_offset'].value = (vp.offset_x, vp.offset_y)
        self.line_program['u_zoom'].value = vp.zoom

        geom = vp._geometry_builder

        # Draw unselected brushes with their individual colors
        for key, (vao, vbo, vertex_count) in geom.brush_vaos.items():
            if visible_brushes is not None and key not in visible_brushes:
                continue
            if key not in selected_keys:
                color = geom.get_brush_color(key)
                self.line_program['u_color'].value = (color[0], color[1], color[2], 1.0)
                try:
                    vao.render(moderngl.LINES)
                except Exception as e:
                    print(f"ERROR rendering brush {key}: {e}")

        # Draw unselected patches (grid lines)
        for key, (vao, vbo, vertex_count) in geom.patch_vaos.items():
            if visible_brushes is not None and key not in visible_brushes:
                continue
            if key not in selected_keys:
                color = geom.get_brush_color(key)
                self.line_program['u_color'].value = (color[0], color[1], color[2], 1.0)
                vao.render(moderngl.LINES)

        # Draw unselected patch diagonals (thinner lines)
        self.ctx.line_width = 0.5
        for key, (vao, vbo, vertex_count) in geom.patch_diagonal_vaos.items():
            if visible_brushes is not None and key not in visible_brushes:
                continue
            if key not in selected_keys:
                color = geom.get_brush_color(key)
                # Slightly darker/more transparent for diagonals
                self.line_program['u_color'].value = (color[0] * 0.7, color[1] * 0.7, color[2] * 0.7, 0.6)
                vao.render(moderngl.LINES)
        self.ctx.line_width = 1.0

        # Draw selected brushes/patches with selection color and thicker lines
        self.ctx.line_width = 2.0
        self.line_program['u_color'].value = vp._selection_color_tuple[:4]

        for key in selected_keys:
            if visible_brushes is not None and key not in visible_brushes:
                continue
            if key in geom.brush_vaos:
                vao = geom.brush_vaos[key][0]
                vao.render(moderngl.LINES)
            if key in geom.patch_vaos:
                geom.patch_vaos[key][0].render(moderngl.LINES)

        # Draw selected patch diagonals (thinner than grid, but thicker than unselected)
        self.ctx.line_width = 1.0
        for key in selected_keys:
            if visible_brushes is not None and key not in visible_brushes:
                continue
            if key in geom.patch_diagonal_vaos:
                # Use selection color but slightly dimmer for diagonals
                sel_color = vp._selection_color_tuple
                self.line_program['u_color'].value = (sel_color[0] * 0.8, sel_color[1] * 0.8, sel_color[2] * 0.8, 0.8)
                geom.patch_diagonal_vaos[key][0].render(moderngl.LINES)

        # Draw selected faces
        self._draw_selected_faces()

        self.ctx.line_width = 1.0

    def _draw_selected_faces(self):
        """Draw selected faces with selection color."""
        vp = self.viewport
        selected_faces = vp.document.selection.selected_faces
        if not selected_faces:
            return

        axis_h, axis_v = vp._get_axes()

        vertices = []
        for entity_idx, brush_idx, face_idx in selected_faces:
            # Get computed vertices
            face_vertices = vp.document.get_brush_vertices(entity_idx, brush_idx)

            if face_idx not in face_vertices:
                continue

            verts = face_vertices[face_idx]
            if len(verts) < 3:
                continue

            for i in range(len(verts)):
                v1 = verts[i]
                v2 = verts[(i + 1) % len(verts)]
                p1 = [v1.x, v1.y, v1.z]
                p2 = [v2.x, v2.y, v2.z]
                vertices.extend([p1[axis_h], p1[axis_v]])
                vertices.extend([p2[axis_h], p2[axis_v]])

        if not vertices:
            return

        vertex_data = np.array(vertices, dtype='f4')
        vbo = self.ctx.buffer(vertex_data.tobytes())
        vao = self.ctx.vertex_array(
            self.line_program,
            [(vbo, '2f', 'in_position')]
        )

        vao.render(moderngl.LINES)

        vao.release()
        vbo.release()

    def draw_entities(self, projection: np.ndarray):
        """Draw entity markers."""
        vp = self.viewport
        geom = vp._geometry_builder

        if self.point_program is None or geom.entity_vao is None or geom.entity_count == 0:
            return

        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)

        self.point_program['u_projection'].write(projection.tobytes())
        self.point_program['u_offset'].value = (vp.offset_x, vp.offset_y)
        self.point_program['u_zoom'].value = vp.zoom
        self.point_program['u_point_size'].value = 12.0

        geom.entity_vao.render(moderngl.POINTS)
