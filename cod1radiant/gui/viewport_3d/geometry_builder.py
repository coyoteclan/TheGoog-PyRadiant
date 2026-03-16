"""Geometry building and VAO management for 3D viewport."""

from __future__ import annotations

import time
import math
from typing import TYPE_CHECKING

import numpy as np
import moderngl

from ...core import (
    Brush,
    get_brush_bounds,
    compute_brush_vertices,
)

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class GeometryBuilder:
    """Handles geometry building and VAO management for the 3D viewport."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

        # Geometry buffers
        self.brush_vaos: dict[tuple[int, int], moderngl.VertexArray] = {}
        self.wireframe_vaos: dict[tuple[int, int], tuple[moderngl.VertexArray, moderngl.Buffer, int]] = {}

        # Texture rendering
        self._default_texture: moderngl.Texture | None = None
        self._texture_cache: dict[str, moderngl.Texture] = {}

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def brush_program(self) -> moderngl.Program | None:
        return self.viewport.brush_program

    @property
    def wireframe_program(self) -> moderngl.Program | None:
        return self.viewport.wireframe_program

    def create_default_texture(self):
        """Create a default checker pattern texture for preview mode."""
        if self.ctx is None:
            return

        # Create a 256x256 checker pattern
        size = 256
        checker_size = 32  # Size of each checker square

        # Create checker pattern data
        data = bytearray(size * size * 4)  # RGBA
        for y in range(size):
            for x in range(size):
                # Determine checker color
                checker_x = (x // checker_size) % 2
                checker_y = (y // checker_size) % 2
                is_light = (checker_x + checker_y) % 2 == 0

                idx = (y * size + x) * 4
                if is_light:
                    # Light gray
                    data[idx] = 180
                    data[idx + 1] = 180
                    data[idx + 2] = 180
                    data[idx + 3] = 255
                else:
                    # Dark gray
                    data[idx] = 120
                    data[idx + 1] = 120
                    data[idx + 2] = 120
                    data[idx + 3] = 255

        # Create texture
        self._default_texture = self.ctx.texture(
            size=(size, size),
            components=4,
            data=bytes(data)
        )

        # Set texture parameters
        self._default_texture.filter = (
            self.ctx.LINEAR_MIPMAP_LINEAR,
            self.ctx.LINEAR
        )
        self._default_texture.build_mipmaps()

        # Enable texture repeat
        self._default_texture.repeat_x = True
        self._default_texture.repeat_y = True

    def rebuild_geometry(self, progress_callback=None):
        """Rebuild brush geometry from document.

        Args:
            progress_callback: Optional callable(current, total) for progress updates
        """
        start_time = time.perf_counter()

        if self.ctx is None or self.brush_program is None:
            print("rebuild_geometry: ctx or brush_program is None")
            return

        try:
            # Clear old VAOs
            for vao in self.brush_vaos.values():
                vao.release()
            self.brush_vaos.clear()

            # Clear old wireframe VAOs
            for vao, vbo, _ in self.wireframe_vaos.values():
                vao.release()
                vbo.release()
            self.wireframe_vaos.clear()

            # Clear patch tessellator VAOs
            self.viewport._patch_tessellator.clear_vaos()

            # Clear frustum culler cache
            self.viewport._frustum_culler.clear()

            # Clear octree
            self.viewport._octree.clear()

            # Count total items first for progress
            all_items = list(self.viewport.document.iter_all_geometry())
            total_items = len(all_items)

            # Build VAO for each brush (skip patches for now)
            brush_count = 0
            patch_count = 0
            vao_time = 0.0

            # Collect brush data for batch renderer
            brush_data = []  # List of (brush, brush_key) tuples

            for idx, (entity_idx, brush_idx, brush) in enumerate(all_items):
                brush_key = (entity_idx, brush_idx)

                if brush.is_regular:
                    brush_count += 1
                    try:
                        # Ensure vertices are computed before creating VAO
                        compute_brush_vertices(brush)
                        vao_start = time.perf_counter()

                        # Create solid VAO
                        vao = self.create_brush_vao(brush, brush_key)
                        if vao:
                            self.brush_vaos[brush_key] = vao

                        # Create wireframe VAO (cached)
                        wire_result = self.create_wireframe_vao(brush, brush_key)
                        if wire_result:
                            self.wireframe_vaos[brush_key] = wire_result

                        # Cache bounds for frustum culling and octree
                        bounds = get_brush_bounds(brush)
                        if bounds:
                            b_min, b_max = bounds
                            self.viewport._frustum_culler.set_brush_bounds(brush_key, b_min, b_max)
                            self.viewport._octree.insert(brush_key, b_min, b_max)

                        vao_time += time.perf_counter() - vao_start

                        # Collect for batch renderer
                        brush_data.append((brush, brush_key))
                    except Exception as e:
                        print(f"Error processing brush {brush_key}: {e}")
                elif brush.is_terrain or brush.is_curve:
                    patch_count += 1
                    try:
                        vao_start = time.perf_counter()

                        patch = brush.patch
                        if patch is None:
                            continue

                        tessellator = self.viewport._patch_tessellator

                        # Create solid patch VAO
                        vao_data = tessellator.create_patch_vao(brush, brush_key)
                        if vao_data:
                            tessellator.patch_vaos[brush_key] = vao_data
                        else:
                            print(f"Warning: No solid VAO created for patch {brush_key}")

                        # Create wireframe VAOs (grid and diagonal separately)
                        grid_result, diag_result = tessellator.create_patch_wireframe_vao(brush, brush_key)
                        if grid_result:
                            tessellator.patch_wireframe_vaos[brush_key] = grid_result
                        else:
                            print(f"Warning: No grid wireframe VAO created for patch {brush_key}")
                        if diag_result:
                            tessellator.patch_diagonal_vaos[brush_key] = diag_result

                        # Cache bounds for frustum culling
                        b_min, b_max = patch.get_bounding_box()
                        self.viewport._frustum_culler.set_brush_bounds(brush_key, b_min, b_max)

                        vao_time += time.perf_counter() - vao_start
                    except Exception as e:
                        print(f"Error processing patch {brush_key}: {e}")

                # Report progress every 50 items
                if progress_callback and (idx % 50 == 0 or idx == total_items - 1):
                    progress_callback(idx + 1, total_items)

            # Build batched renderer with all brushes
            batch_renderer = self.viewport._batch_renderer
            if batch_renderer is not None:
                batch_renderer.set_brushes(brush_data, progress_callback)
                # Update selection state
                selected_brushes = self.viewport.document.selection.selected_brushes
                batch_renderer.update_selection(selected_brushes)

            # Update entity marker renderer
            entity_renderer = self.viewport._entity_renderer
            if entity_renderer is not None:
                entity_renderer.update_entities(self.viewport.document.entities)
                entity_stats = entity_renderer.get_stats()
                print(f"Entity markers: {entity_stats['entity_count']} point entities")

            elapsed = time.perf_counter() - start_time
            print(f"rebuild_geometry: {brush_count} brushes, {patch_count} patches in {elapsed:.3f}s (VAO creation: {vao_time:.3f}s)")
        except Exception as e:
            print(f"Error in rebuild_geometry: {e}")
            import traceback
            traceback.print_exc()

    def rebuild_specific_brushes(self, brush_indices: list[tuple[int, int]]):
        """Rebuild VAOs for specific brushes."""
        if not brush_indices:
            return

        settings = self.viewport._settings_manager

        for entity_idx, brush_idx in brush_indices:
            brush = self.viewport.document.get_brush(entity_idx, brush_idx)
            if brush is None:
                continue

            # Recompute vertices
            compute_brush_vertices(brush)

            # Update octree
            if settings.octree_enabled:
                bounds = get_brush_bounds(brush)
                if bounds:
                    b_min, b_max = bounds
                    self.viewport._octree.update((entity_idx, brush_idx), b_min, b_max)

            # Update batch renderer
            batch_renderer = self.viewport._batch_renderer
            if batch_renderer and settings.batching_enabled:
                batch_renderer.update_brush(brush, (entity_idx, brush_idx))

    def rebuild_moved_brushes(self):
        """Rebuild VAOs for selected (moved) brushes."""
        if self.ctx is None or self.brush_program is None:
            return

        self.viewport.makeCurrent()
        try:
            for entity_idx, brush_idx in self.viewport.document.selection.selected_brushes:
                brush_key = (entity_idx, brush_idx)
                brush = self.viewport.document.get_brush(entity_idx, brush_idx)
                if brush is None:
                    continue

                # Only rebuild VAOs for regular brushes, not patches
                if not brush.is_regular:
                    continue

                # Release old solid VAO if exists
                if brush_key in self.brush_vaos:
                    self.brush_vaos[brush_key].release()

                # Release old wireframe VAO and VBO if exists
                if brush_key in self.wireframe_vaos:
                    vao, vbo, _ = self.wireframe_vaos[brush_key]
                    vao.release()
                    vbo.release()

                # Create new solid VAO with updated geometry
                vao = self.create_brush_vao(brush, brush_key)
                if vao:
                    self.brush_vaos[brush_key] = vao

                # Create new wireframe VAO with updated geometry
                wire_result = self.create_wireframe_vao(brush, brush_key)
                if wire_result:
                    self.wireframe_vaos[brush_key] = wire_result

                # Update frustum culler bounds and octree
                bounds = get_brush_bounds(brush)
                if bounds:
                    b_min, b_max = bounds
                    self.viewport._frustum_culler.set_brush_bounds(brush_key, b_min, b_max)
                    self.viewport._octree.update(brush_key, b_min, b_max)

                # Update batch renderer
                batch_renderer = self.viewport._batch_renderer
                settings = self.viewport._settings_manager
                if batch_renderer and settings.batching_enabled:
                    batch_renderer.update_brush(brush, brush_key)
        finally:
            self.viewport.doneCurrent()

        self.viewport.update()

    def create_brush_vao(self, brush: Brush, brush_key: tuple[int, int]) -> moderngl.VertexArray | None:
        """Create VAO for a single brush."""
        try:
            vertices = []
            indices = []
            vertex_index = 0

            # Compute vertices for all faces
            face_vertices = compute_brush_vertices(brush)

            for face_idx, plane in enumerate(brush.planes):
                face_verts = face_vertices.get(face_idx, [])
                if len(face_verts) < 3:
                    continue

                normal = plane.normal

                # Validate normal
                if (np.isnan(normal.x) or np.isnan(normal.y) or np.isnan(normal.z) or
                    np.isinf(normal.x) or np.isinf(normal.y) or np.isinf(normal.z)):
                    continue

                # Triangulate the face (fan triangulation)
                first_vertex_index = vertex_index

                for vertex in face_verts:
                    # Validate vertex data
                    if (np.isnan(vertex.x) or np.isnan(vertex.y) or np.isnan(vertex.z) or
                        np.isinf(vertex.x) or np.isinf(vertex.y) or np.isinf(vertex.z)):
                        continue

                    # Position, Normal, TexCoord
                    vertices.extend([
                        float(vertex.x), float(vertex.y), float(vertex.z),
                        float(normal.x), float(normal.y), float(normal.z),
                        0.0, 0.0  # Placeholder texcoords
                    ])
                    vertex_index += 1

                # Create triangles
                num_verts = vertex_index - first_vertex_index
                for i in range(1, num_verts - 1):
                    indices.extend([
                        first_vertex_index,
                        first_vertex_index + i,
                        first_vertex_index + i + 1
                    ])

            if not vertices or not indices:
                return None

            # Validate data before creating buffers
            vertices_array = np.array(vertices, dtype='f4')
            indices_array = np.array(indices, dtype='i4')

            if vertices_array.size == 0 or indices_array.size == 0:
                return None

            if np.isnan(vertices_array).any() or np.isinf(vertices_array).any():
                print(f"Warning: Invalid vertex data for brush {brush_key}")
                return None

            vbo = self.ctx.buffer(vertices_array.tobytes())
            ibo = self.ctx.buffer(indices_array.tobytes())

            vao = self.ctx.vertex_array(
                self.brush_program,
                [(vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
                ibo
            )

            return vao
        except Exception as e:
            print(f"Error creating VAO for brush {brush_key}: {e}")
            return None

    def create_wireframe_vao(self, brush: Brush, brush_key: tuple[int, int]) -> tuple[moderngl.VertexArray, moderngl.Buffer, int] | None:
        """Create wireframe VAO for a brush with face normals for backface culling."""
        try:
            # Each vertex needs: position (3f) + normal (3f)
            vertex_data = []

            # Compute vertices for all faces
            face_vertices = compute_brush_vertices(brush)

            for face_idx, plane in enumerate(brush.planes):
                face_verts = face_vertices.get(face_idx, [])
                if len(face_verts) < 3:
                    continue

                # Get face normal from plane
                normal = plane.normal

                # Validate normal
                if (math.isnan(normal.x) or math.isnan(normal.y) or math.isnan(normal.z)):
                    # Fallback: calculate from vertices
                    v0 = face_verts[0]
                    v1 = face_verts[1]
                    v2 = face_verts[2]
                    edge1_x, edge1_y, edge1_z = v1.x - v0.x, v1.y - v0.y, v1.z - v0.z
                    edge2_x, edge2_y, edge2_z = v2.x - v0.x, v2.y - v0.y, v2.z - v0.z
                    nx = edge1_y * edge2_z - edge1_z * edge2_y
                    ny = edge1_z * edge2_x - edge1_x * edge2_z
                    nz = edge1_x * edge2_y - edge1_y * edge2_x
                    norm_len = (nx*nx + ny*ny + nz*nz) ** 0.5
                    if norm_len > 0:
                        nx, ny, nz = nx / norm_len, ny / norm_len, nz / norm_len
                    else:
                        nx, ny, nz = 0.0, 0.0, 1.0
                else:
                    nx, ny, nz = normal.x, normal.y, normal.z

                # Draw edges with face normal
                num_verts = len(face_verts)
                for i in range(num_verts):
                    v1 = face_verts[i]
                    v2 = face_verts[(i + 1) % num_verts]

                    # Validate vertices
                    if (math.isnan(v1.x) or math.isnan(v1.y) or math.isnan(v1.z) or
                        math.isinf(v1.x) or math.isinf(v1.y) or math.isinf(v1.z)):
                        continue
                    if (math.isnan(v2.x) or math.isnan(v2.y) or math.isnan(v2.z) or
                        math.isinf(v2.x) or math.isinf(v2.y) or math.isinf(v2.z)):
                        continue

                    # Vertex 1: position + normal
                    vertex_data.extend([float(v1.x), float(v1.y), float(v1.z)])
                    vertex_data.extend([float(nx), float(ny), float(nz)])
                    # Vertex 2: position + normal
                    vertex_data.extend([float(v2.x), float(v2.y), float(v2.z)])
                    vertex_data.extend([float(nx), float(ny), float(nz)])

            if not vertex_data:
                return None

            vertices = np.array(vertex_data, dtype='f4')

            if vertices.size == 0 or np.isnan(vertices).any() or np.isinf(vertices).any():
                return None

            vbo = self.ctx.buffer(vertices.tobytes())

            vao = self.ctx.vertex_array(
                self.wireframe_program,
                [(vbo, '3f 3f', 'in_position', 'in_normal')]
            )

            # vertex_count = total floats / 6 floats per vertex
            vertex_count = len(vertex_data) // 6
            return vao, vbo, vertex_count
        except Exception as e:
            print(f"Error creating wireframe VAO for brush {brush_key}: {e}")
            return None

    @property
    def default_texture(self) -> moderngl.Texture | None:
        return self._default_texture
