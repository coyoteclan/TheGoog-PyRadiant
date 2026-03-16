"""Geometry building (VAO/VBO creation) for 2D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL

from ...core import (
    Brush, ui_state, compute_brush_vertices, get_brush_bounds,
)


class GeometryBuilder:
    """Handles brush/patch VAO creation for 2D viewport."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

        # Brush/Patch VAOs: dict[(entity_idx, brush_idx), (vao, vbo, vertex_count)]
        self.brush_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}
        self.patch_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}
        # Separate VAOs for patch diagonal lines (thinner rendering)
        self.patch_diagonal_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}

        # Brush colors based on content flags ((entity_idx, brush_idx) -> RGB tuple)
        self._brush_colors: dict[tuple[int, int], tuple[float, float, float]] = {}

        # Entity VAO
        self.entity_vao: moderngl.VertexArray | None = None
        self.entity_vbo: moderngl.Buffer | None = None
        self.entity_count: int = 0

        self._geometry_dirty = True

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def line_program(self) -> moderngl.Program | None:
        return self.viewport.line_program

    @property
    def point_program(self) -> moderngl.Program | None:
        return self.viewport.point_program

    def mark_dirty(self):
        """Mark geometry as needing rebuild."""
        self._geometry_dirty = True

    def is_dirty(self) -> bool:
        """Check if geometry needs rebuild."""
        return self._geometry_dirty

    def rebuild(self):
        """Rebuild brush and patch VAOs."""
        if self.ctx is None or self.line_program is None:
            return

        v = self.viewport
        axis_h, axis_v = v._get_axes()

        # Clear old VAOs and VBOs
        for vao, vbo, _ in self.brush_vaos.values():
            vao.release()
            vbo.release()
        self.brush_vaos.clear()

        for vao, vbo, _ in self.patch_vaos.values():
            vao.release()
            vbo.release()
        self.patch_vaos.clear()

        for vao, vbo, _ in self.patch_diagonal_vaos.values():
            vao.release()
            vbo.release()
        self.patch_diagonal_vaos.clear()

        # Clear brush colors cache
        self._brush_colors.clear()

        # Build VAOs for each brush/patch
        for entity_idx, brush_idx, brush in v.document.iter_all_geometry():
            key = (entity_idx, brush_idx)

            # Use UIStateManager for visibility check
            if ui_state.is_brush_hidden(entity_idx, brush_idx):
                continue

            if brush.is_regular:
                vao_data = self._create_brush_vao(brush, entity_idx, brush_idx, axis_h, axis_v)
                if vao_data:
                    self.brush_vaos[key] = vao_data
                    self._brush_colors[key] = self._get_brush_color(brush)

            elif brush.is_patch:
                try:
                    vao_data, diag_vao_data = self._create_patch_vao(brush, axis_h, axis_v)
                    if vao_data:
                        self.patch_vaos[key] = vao_data
                        self._brush_colors[key] = self._get_brush_color(brush)
                    if diag_vao_data:
                        self.patch_diagonal_vaos[key] = diag_vao_data
                except Exception as e:
                    print(f"Error creating 2D patch VAO for {key}: {e}")
                    import traceback
                    traceback.print_exc()

        # Build entity markers
        self._rebuild_entity_markers(axis_h, axis_v)

        self._geometry_dirty = False

    def _create_brush_vao(
        self,
        brush: Brush,
        entity_idx: int,
        brush_idx: int,
        axis_h: int,
        axis_v: int
    ) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create VAO for a brush (2D line representation).

        Only draws edges from faces that are visible (facing the camera) when backface culling is enabled.
        """
        lines = []
        vp = self.viewport

        # Check if backface culling is enabled for 2D view
        backface_culling = vp._backface_culling_2d if hasattr(vp, '_backface_culling_2d') else True

        # Determine which axis the camera is looking along (the "depth" axis)
        depth_axis = 3 - axis_h - axis_v

        # Get computed vertices from document cache
        face_vertices = vp.document.get_brush_vertices(entity_idx, brush_idx)

        for face_idx, verts in face_vertices.items():
            if len(verts) < 3:
                continue

            # Only perform backface culling if enabled
            if backface_culling:
                # Compute face normal from vertices
                v0 = np.array([verts[0].x, verts[0].y, verts[0].z])
                v1 = np.array([verts[1].x, verts[1].y, verts[1].z])
                v2 = np.array([verts[2].x, verts[2].y, verts[2].z])
                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = np.cross(edge1, edge2)
                norm_len = np.linalg.norm(normal)
                if norm_len > 0:
                    normal = normal / norm_len
                else:
                    continue

                if normal[depth_axis] <= 0:
                    continue

            n = len(verts)
            for i in range(n):
                pt1 = verts[i]
                pt2 = verts[(i + 1) % n]
                p1 = [pt1.x, pt1.y, pt1.z]
                p2 = [pt2.x, pt2.y, pt2.z]
                lines.extend([p1[axis_h], p1[axis_v], p2[axis_h], p2[axis_v]])

        if not lines:
            return None

        vertices = np.array(lines, dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())

        vao = self.ctx.vertex_array(
            self.line_program,
            [(vbo, '2f', 'in_position')]
        )

        return (vao, vbo, len(lines) // 2)

    def _tessellate_bezier_patch(self, patch, subdivisions: int = 4):
        """Tessellate a Bezier patch into a grid of vertices.

        Bezier patches use 3x3 control point blocks for quadratic curves.
        This function evaluates the Bezier surface at regular intervals.

        Returns:
            List of lists of (x, y, z) tuples representing the tessellated grid
        """
        rows = patch.rows
        cols = patch.cols

        # For Bezier, we need (2n+1) control points for n patches
        # Each 3x3 block of control points defines one Bezier patch
        num_patches_row = (rows - 1) // 2
        num_patches_col = (cols - 1) // 2

        if num_patches_row < 1 or num_patches_col < 1:
            # Not enough control points for Bezier, treat as terrain
            return None

        # Output grid size
        out_rows = num_patches_row * subdivisions + 1
        out_cols = num_patches_col * subdivisions + 1

        result = []

        for out_row in range(out_rows):
            row_verts = []
            # Which Bezier patch row and local t parameter
            patch_row = min(out_row // subdivisions, num_patches_row - 1)
            t_row = (out_row % subdivisions) / subdivisions if out_row < out_rows - 1 else 1.0
            if out_row == out_rows - 1:
                patch_row = num_patches_row - 1
                t_row = 1.0

            for out_col in range(out_cols):
                # Which Bezier patch col and local s parameter
                patch_col = min(out_col // subdivisions, num_patches_col - 1)
                t_col = (out_col % subdivisions) / subdivisions if out_col < out_cols - 1 else 1.0
                if out_col == out_cols - 1:
                    patch_col = num_patches_col - 1
                    t_col = 1.0

                # Get the 3x3 control points for this Bezier patch
                base_row = patch_row * 2
                base_col = patch_col * 2

                # Evaluate quadratic Bezier in both directions
                # B(t) = (1-t)^2 * P0 + 2*(1-t)*t * P1 + t^2 * P2
                def bezier_weights(t):
                    return [(1 - t) ** 2, 2 * (1 - t) * t, t ** 2]

                w_row = bezier_weights(t_row)
                w_col = bezier_weights(t_col)

                x, y, z = 0.0, 0.0, 0.0
                for i in range(3):
                    for j in range(3):
                        weight = w_row[i] * w_col[j]
                        cp = patch.vertices[base_row + i][base_col + j]
                        x += weight * cp.x
                        y += weight * cp.y
                        z += weight * cp.z

                row_verts.append((x, y, z))
            result.append(row_verts)

        return result

    def _create_patch_vao(self, brush: Brush, axis_h: int, axis_v: int) -> tuple[
        tuple[moderngl.VertexArray, moderngl.Buffer, int] | None,
        tuple[moderngl.VertexArray, moderngl.Buffer, int] | None
    ]:
        """Create VAOs for a patch (2D grid line representation).

        Returns:
            Tuple of (grid_vao_data, diagonal_vao_data) where each is (vao, vbo, vertex_count) or None
        """
        grid_lines = []
        diagonal_lines = []

        # Get the patch data from the brush
        patch = brush.patch
        if patch is None:
            return None, None

        # For Bezier curves (patchDef5), tessellate first
        if brush.is_curve:
            tessellated = self._tessellate_bezier_patch(patch, subdivisions=4)
            if tessellated is None:
                # Fallback to direct rendering
                tessellated = [[(v.x, v.y, v.z) for v in row] for row in patch.vertices]
            rows = len(tessellated)
            cols = len(tessellated[0]) if tessellated else 0
        else:
            # Terrain - use vertices directly
            tessellated = [[(v.x, v.y, v.z) for v in row] for row in patch.vertices]
            rows = patch.rows
            cols = patch.cols

        # Helper to get axis value from tuple
        def get_axis(v, axis):
            return v[0] if axis == 0 else (v[1] if axis == 1 else v[2])

        # Draw horizontal lines (along columns)
        for row_idx in range(rows):
            for col_idx in range(cols - 1):
                v1 = tessellated[row_idx][col_idx]
                v2 = tessellated[row_idx][col_idx + 1]

                w1h = get_axis(v1, axis_h)
                w1v = get_axis(v1, axis_v)
                w2h = get_axis(v2, axis_h)
                w2v = get_axis(v2, axis_v)

                grid_lines.extend([w1h, w1v, w2h, w2v])

        # Draw vertical lines (along rows)
        for col_idx in range(cols):
            for row_idx in range(rows - 1):
                v1 = tessellated[row_idx][col_idx]
                v2 = tessellated[row_idx + 1][col_idx]

                w1h = get_axis(v1, axis_h)
                w1v = get_axis(v1, axis_v)
                w2h = get_axis(v2, axis_h)
                w2v = get_axis(v2, axis_v)

                grid_lines.extend([w1h, w1v, w2h, w2v])

        # Draw diagonal edges (split each quad into two triangles) - separate VAO for thinner lines
        # Diagonal goes from [row][col+1] to [row+1][col] to match CoD Radiant
        for row_idx in range(rows - 1):
            for col_idx in range(cols - 1):
                # Diagonal from v01 to v10 (top-right to bottom-left in grid terms)
                v1 = tessellated[row_idx][col_idx + 1]      # v01
                v2 = tessellated[row_idx + 1][col_idx]      # v10

                w1h = get_axis(v1, axis_h)
                w1v = get_axis(v1, axis_v)
                w2h = get_axis(v2, axis_h)
                w2v = get_axis(v2, axis_v)

                diagonal_lines.extend([w1h, w1v, w2h, w2v])

        # Create grid VAO
        grid_vao_data = None
        if grid_lines:
            vertices = np.array(grid_lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            grid_vao_data = (vao, vbo, len(grid_lines) // 2)

        # Create diagonal VAO (separate for thinner rendering)
        diagonal_vao_data = None
        if diagonal_lines:
            vertices = np.array(diagonal_lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            diagonal_vao_data = (vao, vbo, len(diagonal_lines) // 2)

        return grid_vao_data, diagonal_vao_data

    def _rebuild_entity_markers(self, axis_h: int, axis_v: int):
        """Rebuild entity marker VAO."""
        if self.ctx is None or self.point_program is None:
            return

        vp = self.viewport
        points = []  # x, y, r, g, b, a

        for entity_idx, entity in vp.document.iter_point_entities():
            origin = entity.origin
            if origin is None:
                continue

            # origin is Vec3
            pos = [origin.x, origin.y, origin.z]
            wx, wy = pos[axis_h], pos[axis_v]

            # Determine color based on classname
            classname = entity.classname
            if classname.startswith("light"):
                r, g, b, a = 1.0, 1.0, 0.0, 1.0  # Yellow
            elif classname.startswith("info_player"):
                r, g, b, a = 0.0, 1.0, 0.0, 1.0  # Green
            else:
                r, g, b, a = 0.0, 0.8, 1.0, 1.0  # Cyan

            points.extend([wx, wy, r, g, b, a])

        if points:
            vertices = np.array(points, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())

            # Release old VAO and VBO
            if self.entity_vao:
                self.entity_vao.release()
            if self.entity_vbo:
                self.entity_vbo.release()

            self.entity_vao = self.ctx.vertex_array(
                self.point_program,
                [(vbo, '2f 4f', 'in_position', 'in_color')]
            )
            self.entity_vbo = vbo
            self.entity_count = len(points) // 6
        else:
            self.entity_count = 0

    def rebuild_single_brush(self, entity_idx: int, brush_idx: int):
        """Rebuild VAO for a single brush (after geometry change)."""
        if self.ctx is None or self.line_program is None:
            return

        vp = self.viewport
        axis_h, axis_v = vp._get_axes()
        key = (entity_idx, brush_idx)

        # Get the brush
        brush = vp.document.get_brush(entity_idx, brush_idx)
        if brush is None:
            return

        # Release old VAO and VBO if exists
        if key in self.brush_vaos:
            vao, vbo, _ = self.brush_vaos[key]
            vao.release()
            vbo.release()
            del self.brush_vaos[key]

        if key in self.patch_vaos:
            vao, vbo, _ = self.patch_vaos[key]
            vao.release()
            vbo.release()
            del self.patch_vaos[key]

        # Remove old color
        if key in self._brush_colors:
            del self._brush_colors[key]

        # Create new VAO
        if brush.is_regular:
            vao_data = self._create_brush_vao(brush, entity_idx, brush_idx, axis_h, axis_v)
            if vao_data:
                self.brush_vaos[key] = vao_data
                self._brush_colors[key] = self._get_brush_color(brush)
        elif brush.is_patch:
            vao_data = self._create_patch_vao(brush, axis_h, axis_v)
            if vao_data:
                self.patch_vaos[key] = vao_data
                self._brush_colors[key] = self._get_brush_color(brush)

    def _get_brush_color(self, brush: Brush) -> tuple[float, float, float]:
        """Determine the 2D viewport color for a brush/patch based on content flags."""
        vp = self.viewport

        is_terrain = brush.is_terrain
        is_curve = brush.is_curve

        content_flag = 0
        if brush.is_regular and brush.planes:
            for plane in brush.planes:
                flag = getattr(plane, 'content_flags', 0)
                if flag != 0:
                    content_flag = flag
                    break

        # Content flag values
        DETAIL_FLAG = 134217728
        NON_COLLIDING_FLAG = 134217732
        WEAPON_CLIP_FLAG = 134226048

        if content_flag == DETAIL_FLAG:
            return vp._brush_colors_2d["detail"]
        elif content_flag == WEAPON_CLIP_FLAG:
            return vp._brush_colors_2d["weapon_clip"]
        elif content_flag == NON_COLLIDING_FLAG:
            return vp._brush_colors_2d["non_colliding"]

        if is_terrain:
            return vp._brush_colors_2d["terrain"]
        elif is_curve:
            return vp._brush_colors_2d["curves"]

        return vp._brush_colors_2d["structural"]

    def get_brush_color(self, key: tuple[int, int]) -> tuple[float, float, float]:
        """Get cached color for a brush by (entity_idx, brush_idx)."""
        return self._brush_colors.get(key, self.viewport._brush_colors_2d["structural"])

    def remove_brush(self, entity_idx: int, brush_idx: int):
        """Remove a brush from VAO cache."""
        key = (entity_idx, brush_idx)

        if key in self.brush_vaos:
            vao, vbo, _ = self.brush_vaos[key]
            vao.release()
            vbo.release()
            del self.brush_vaos[key]

        if key in self.patch_vaos:
            vao, vbo, _ = self.patch_vaos[key]
            vao.release()
            vbo.release()
            del self.patch_vaos[key]

        if key in self.patch_diagonal_vaos:
            vao, vbo, _ = self.patch_diagonal_vaos[key]
            vao.release()
            vbo.release()
            del self.patch_diagonal_vaos[key]

        if key in self._brush_colors:
            del self._brush_colors[key]
