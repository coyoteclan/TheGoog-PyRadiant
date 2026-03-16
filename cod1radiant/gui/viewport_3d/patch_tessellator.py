"""Patch tessellation and VAO creation for terrain and curves."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

from ...core import Brush

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class PatchTessellator:
    """Handles tessellation and VAO creation for patches (terrain and curves)."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

        # Patch geometry buffers - store (VAO, VBO, vertex_count) for proper cleanup
        self.patch_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}
        self.patch_wireframe_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}
        self.patch_diagonal_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def brush_program(self) -> moderngl.Program | None:
        return self.viewport.brush_program

    @property
    def wireframe_program(self) -> moderngl.Program | None:
        return self.viewport.wireframe_program

    def tessellate_bezier_patch(self, patch, subdivisions: int = 4):
        """Tessellate a Bezier patch into a grid of vertices.

        Bezier patches use 3x3 control point blocks for quadratic curves.
        This function evaluates the Bezier surface at regular intervals.

        Returns:
            List of lists of (x, y, z, u, v) tuples representing the tessellated grid
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

                x, y, z, u, v = 0.0, 0.0, 0.0, 0.0, 0.0
                for i in range(3):
                    for j in range(3):
                        weight = w_row[i] * w_col[j]
                        cp = patch.vertices[base_row + i][base_col + j]
                        x += weight * cp.x
                        y += weight * cp.y
                        z += weight * cp.z
                        u += weight * cp.u
                        v += weight * cp.v

                row_verts.append((x, y, z, u, v))
            result.append(row_verts)

        return result

    def create_patch_vao(self, brush: Brush, brush_key: tuple[int, int]) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create solid VAO for a patch (terrain/curve)."""
        if self.ctx is None or self.brush_program is None:
            return None

        try:
            patch = brush.patch
            if patch is None:
                return None

            # Route to appropriate method based on patch type
            if brush.is_curve:
                return self._create_bezier_vao(patch)
            else:
                return self._create_terrain_vao(patch)

        except Exception:
            return None

    def _create_terrain_vao(self, patch) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create VAO for terrain patch (patchTerrainDef3).

        Terrain uses vertices directly with turned_edge flag for diagonal control.
        The turned_edge flag on v00 controls which diagonal splits the quad:
        - turned_edge=0: diagonal from v00 to v11 (default)
        - turned_edge=1: diagonal from v01 to v10 (flipped/turned)
        """
        rows = patch.rows
        cols = patch.cols

        if rows < 2 or cols < 2:
            return None

        vertices = []

        for row in range(rows - 1):
            for col in range(cols - 1):
                # Get quad corners directly from patch vertices
                # v00 = current row/col, v01 = same row, next col
                # v10 = next row, same col, v11 = next row, next col
                v00 = patch.vertices[row][col]
                v01 = patch.vertices[row][col + 1]
                v10 = patch.vertices[row + 1][col]
                v11 = patch.vertices[row + 1][col + 1]

                # turned_edge flag on v00 determines diagonal direction
                turned = v00.turned_edge

                if turned == 0:
                    # Default diagonal: v00-v11
                    # Two triangles sharing the v00-v11 diagonal
                    # Triangle 1: v00, v10, v11 (lower-right)
                    # Triangle 2: v00, v11, v01 (upper-left)
                    tri1 = [v00, v10, v11]
                    tri2 = [v00, v11, v01]
                else:
                    # Turned diagonal: v01-v10
                    # Two triangles sharing the v01-v10 diagonal
                    # Triangle 1: v00, v10, v01 (lower-left)
                    # Triangle 2: v10, v11, v01 (upper-right)
                    tri1 = [v00, v10, v01]
                    tri2 = [v10, v11, v01]

                # Calculate per-triangle normals for proper lighting
                for tri in [tri1, tri2]:
                    # Edge vectors from first vertex
                    e1 = np.array([tri[1].x - tri[0].x, tri[1].y - tri[0].y, tri[1].z - tri[0].z])
                    e2 = np.array([tri[2].x - tri[0].x, tri[2].y - tri[0].y, tri[2].z - tri[0].z])

                    # Normal = e1 x e2
                    normal = np.cross(e1, e2)
                    norm_len = np.linalg.norm(normal)
                    if norm_len > 0:
                        normal = normal / norm_len
                    else:
                        normal = np.array([0.0, 0.0, 1.0])
                    nx, ny, nz = float(normal[0]), float(normal[1]), float(normal[2])

                    # Add vertices for this triangle (front face)
                    for v in tri:
                        vertices.extend([
                            float(v.x), float(v.y), float(v.z),
                            nx, ny, nz,
                            float(v.u), float(v.v)
                        ])

                    # Add vertices for back face (reversed winding, negated normal)
                    for v in reversed(tri):
                        vertices.extend([
                            float(v.x), float(v.y), float(v.z),
                            -nx, -ny, -nz,
                            float(v.u), float(v.v)
                        ])

        if not vertices:
            return None

        print(f"[TERRAIN DEBUG] Created {len(vertices)//8} vertices, {len(vertices)//8//3} triangles for {rows}x{cols} patch")
        return self._finalize_vao(vertices)

    def _create_bezier_vao(self, patch) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create VAO for bezier curve patch (patchDef5).

        Bezier patches are tessellated from control points. No turned_edge needed.
        """
        # Use subdivision parameter from patch params
        subdivisions = max(1, patch.params.subdivision // 2)

        tessellated = self.tessellate_bezier_patch(patch, subdivisions=subdivisions)

        if tessellated is None:
            # Fallback: render control points directly (like terrain but without turned_edge)
            tessellated = [[(v.x, v.y, v.z, v.u, v.v) for v in row] for row in patch.vertices]

        rows = len(tessellated)
        cols = len(tessellated[0]) if tessellated else 0

        if rows < 2 or cols < 2:
            return None

        vertices = []

        for row in range(rows - 1):
            for col in range(cols - 1):
                v00 = tessellated[row][col]
                v01 = tessellated[row][col + 1]
                v10 = tessellated[row + 1][col]
                v11 = tessellated[row + 1][col + 1]

                # Triangles with consistent winding order
                # Triangle 1: v00, v10, v11
                # Triangle 2: v00, v11, v01
                tris = [
                    (v00, v10, v11),
                    (v00, v11, v01)
                ]

                for tri in tris:
                    # Calculate normal using cross product for this triangle
                    e1 = np.array([tri[1][0] - tri[0][0], tri[1][1] - tri[0][1], tri[1][2] - tri[0][2]])
                    e2 = np.array([tri[2][0] - tri[0][0], tri[2][1] - tri[0][1], tri[2][2] - tri[0][2]])

                    normal = np.cross(e1, e2)
                    norm_len = np.linalg.norm(normal)
                    if norm_len > 0:
                        normal = normal / norm_len
                    else:
                        normal = np.array([0.0, 0.0, 1.0])
                    nx, ny, nz = float(normal[0]), float(normal[1]), float(normal[2])

                    # Add front face
                    for v in tri:
                        vertices.extend([
                            float(v[0]), float(v[1]), float(v[2]),
                            nx, ny, nz,
                            float(v[3]), float(v[4])
                        ])

                    # Add back face (reversed winding, negated normal)
                    for v in reversed(tri):
                        vertices.extend([
                            float(v[0]), float(v[1]), float(v[2]),
                            -nx, -ny, -nz,
                            float(v[3]), float(v[4])
                        ])

        if not vertices:
            return None

        return self._finalize_vao(vertices)

    def _finalize_vao(self, vertices: list) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create VAO from vertex list."""
        vertices_array = np.array(vertices, dtype='f4')

        if np.isnan(vertices_array).any() or np.isinf(vertices_array).any():
            return None

        vbo = self.ctx.buffer(vertices_array.tobytes())
        vao = self.ctx.vertex_array(
            self.brush_program,
            [(vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')]
        )

        # vertex_count = total floats / 8 floats per vertex
        vertex_count = len(vertices) // 8
        return (vao, vbo, vertex_count)

    def create_patch_wireframe_vao(self, brush: Brush, brush_key: tuple[int, int]) -> tuple[
        tuple[moderngl.VertexArray, moderngl.Buffer, int] | None,
        tuple[moderngl.VertexArray, moderngl.Buffer, int] | None
    ]:
        """Create wireframe VAOs for a patch (grid lines and diagonals separately).

        For Bezier curves (patchDef5): Shows only control points (no tessellation)
        For Terrain (patchTerrainDef3): Shows actual vertex grid with diagonals
        """
        if self.ctx is None or self.wireframe_program is None:
            return None, None

        try:
            patch = brush.patch
            if patch is None:
                return None, None

            grid_vertex_data = []
            diagonal_vertex_data = []

            # For Bezier curves (patchDef5), use control points directly (no tessellation)
            # This matches the original Radiant behavior where wireframe shows control mesh
            # For Terrain, use vertices directly with turned_edge flag for diagonals
            # Vertex format: (x, y, z, u, v, turned_edge)
            tessellated = [[(v.x, v.y, v.z, v.u, v.v, v.turned_edge) for v in row] for row in patch.vertices]

            # Always use actual dimensions
            rows = len(tessellated)
            cols = len(tessellated[0]) if tessellated else 0

            # Grid lines (horizontal and vertical) with per-quad normals
            for row in range(rows - 1):
                for col in range(cols - 1):
                    # Get quad corners (x, y, z, u, v, turned_edge)
                    v00 = tessellated[row][col]
                    v10 = tessellated[row + 1][col]
                    v01 = tessellated[row][col + 1]
                    v11 = tessellated[row + 1][col + 1]

                    # Calculate average normal for this quad
                    edge1 = np.array([v10[0] - v00[0], v10[1] - v00[1], v10[2] - v00[2]])
                    edge2 = np.array([v01[0] - v00[0], v01[1] - v00[1], v01[2] - v00[2]])
                    normal = np.cross(edge1, edge2)
                    norm_len = np.linalg.norm(normal)
                    if norm_len > 0:
                        normal = normal / norm_len
                    else:
                        normal = np.array([0.0, 0.0, 1.0])

                    nx, ny, nz = float(normal[0]), float(normal[1]), float(normal[2])

                    # Horizontal line (top edge of quad): v00 -> v01
                    if row == 0:  # Only draw top edge for first row
                        grid_vertex_data.extend([float(v00[0]), float(v00[1]), float(v00[2]), nx, ny, nz])
                        grid_vertex_data.extend([float(v01[0]), float(v01[1]), float(v01[2]), nx, ny, nz])

                    # Horizontal line (bottom edge): v10 -> v11
                    grid_vertex_data.extend([float(v10[0]), float(v10[1]), float(v10[2]), nx, ny, nz])
                    grid_vertex_data.extend([float(v11[0]), float(v11[1]), float(v11[2]), nx, ny, nz])

                    # Vertical line (left edge of quad): v00 -> v10
                    if col == 0:  # Only draw left edge for first column
                        grid_vertex_data.extend([float(v00[0]), float(v00[1]), float(v00[2]), nx, ny, nz])
                        grid_vertex_data.extend([float(v10[0]), float(v10[1]), float(v10[2]), nx, ny, nz])

                    # Vertical line (right edge): v01 -> v11
                    grid_vertex_data.extend([float(v01[0]), float(v01[1]), float(v01[2]), nx, ny, nz])
                    grid_vertex_data.extend([float(v11[0]), float(v11[1]), float(v11[2]), nx, ny, nz])

                    # Only show diagonals for terrain patches, not for Bezier curves
                    # Bezier curves show only the control point grid (like original Radiant)
                    if not brush.is_curve:
                        # Use turned_edge flag from v00 to determine diagonal direction
                        # (same logic as solid rendering)
                        turned = v00[5] if len(v00) > 5 else 0

                        if turned == 0:
                            # Default diagonal: v00-v11
                            diagonal_vertex_data.extend([float(v00[0]), float(v00[1]), float(v00[2]), nx, ny, nz])
                            diagonal_vertex_data.extend([float(v11[0]), float(v11[1]), float(v11[2]), nx, ny, nz])
                        else:
                            # Turned/flipped diagonal: v01-v10
                            diagonal_vertex_data.extend([float(v01[0]), float(v01[1]), float(v01[2]), nx, ny, nz])
                            diagonal_vertex_data.extend([float(v10[0]), float(v10[1]), float(v10[2]), nx, ny, nz])

            # Create grid VAO
            grid_result = None
            if grid_vertex_data:
                vertices = np.array(grid_vertex_data, dtype='f4')
                vbo = self.ctx.buffer(vertices.tobytes())
                vao = self.ctx.vertex_array(
                    self.wireframe_program,
                    [(vbo, '3f 3f', 'in_position', 'in_normal')]
                )
                vertex_count = len(grid_vertex_data) // 6
                grid_result = (vao, vbo, vertex_count)

            # Create diagonal VAO
            diagonal_result = None
            if diagonal_vertex_data:
                vertices = np.array(diagonal_vertex_data, dtype='f4')
                vbo = self.ctx.buffer(vertices.tobytes())
                vao = self.ctx.vertex_array(
                    self.wireframe_program,
                    [(vbo, '3f 3f', 'in_position', 'in_normal')]
                )
                vertex_count = len(diagonal_vertex_data) // 6
                diagonal_result = (vao, vbo, vertex_count)

            return grid_result, diagonal_result
        except Exception as e:
            print(f"Error creating patch wireframe VAO for {brush_key}: {e}")
            import traceback
            traceback.print_exc()
            return None, None

    def clear_vaos(self):
        """Clear and release all patch VAOs."""
        for vao, vbo, _ in self.patch_vaos.values():
            vao.release()
            vbo.release()
        self.patch_vaos.clear()

        for vao, vbo, _ in self.patch_wireframe_vaos.values():
            vao.release()
            vbo.release()
        self.patch_wireframe_vaos.clear()

        for vao, vbo, _ in self.patch_diagonal_vaos.values():
            vao.release()
            vbo.release()
        self.patch_diagonal_vaos.clear()

    def store_patch_vaos(self, brush_key: tuple[int, int],
                         solid_vao: tuple | None,
                         grid_vao: tuple | None,
                         diagonal_vao: tuple | None):
        """Store created patch VAOs."""
        if solid_vao:
            self.patch_vaos[brush_key] = solid_vao
        if grid_vao:
            self.patch_wireframe_vaos[brush_key] = grid_vao
        if diagonal_vao:
            self.patch_diagonal_vaos[brush_key] = diagonal_vao
