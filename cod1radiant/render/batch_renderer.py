"""Batched rendering for efficient brush drawing with minimal draw calls.

Supports two rendering modes:
1. Single-texture mode: All faces use the same texture (or solid color)
2. Multi-texture mode: Faces are grouped by texture for per-face texturing

Multi-texture rendering works by:
- Grouping faces by their shader/texture name
- Creating separate VAOs for each texture group
- Rendering each group with its corresponding GPU texture bound
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable
import numpy as np

from ..core.texture_manager import compute_uv, get_texture_manager

if TYPE_CHECKING:
    import moderngl
    from ..core import Brush

from ..core import compute_brush_vertices


class BrushBatch:
    """
    A batch of brush geometry combined into a single VAO for efficient rendering.

    Instead of one draw call per brush, this combines multiple brushes into
    a single VBO/VAO, drastically reducing draw call overhead.

    Uses (entity_idx, brush_idx) tuples as brush keys.
    """

    __slots__ = (
        'ctx', 'program', 'vao', 'vbo', 'ibo',
        'vertex_count', 'index_count',
        'brush_keys', 'brush_offsets', 'capacity', 'dirty'
    )

    def __init__(self, ctx: "moderngl.Context", program: "moderngl.Program", initial_capacity: int = 10000):
        """
        Initialize a brush batch.

        Args:
            ctx: ModernGL context
            program: Shader program to use
            initial_capacity: Initial vertex capacity (will grow as needed)
        """
        self.ctx = ctx
        self.program = program
        self.capacity = initial_capacity

        # Buffers - will be created on first build
        self.vao: "moderngl.VertexArray | None" = None
        self.vbo: "moderngl.Buffer | None" = None
        self.ibo: "moderngl.Buffer | None" = None

        # Tracking
        self.vertex_count = 0
        self.index_count = 0
        self.brush_keys: set[tuple[int, int]] = set()
        self.brush_offsets: dict[tuple[int, int], tuple[int, int]] = {}  # brush_key -> (vertex_offset, index_offset)
        self.dirty = True

    def release(self):
        """Release GPU resources."""
        if self.vao:
            self.vao.release()
            self.vao = None
        if self.vbo:
            self.vbo.release()
            self.vbo = None
        if self.ibo:
            self.ibo.release()
            self.ibo = None

    def build(self, brush_data: list[tuple["Brush", tuple[int, int]]]):
        """
        Build the batch from a list of brushes with their keys.

        Args:
            brush_data: List of (Brush, brush_key) tuples where brush_key is (entity_idx, brush_idx)
        """
        if not brush_data:
            self.release()
            self.vertex_count = 0
            self.index_count = 0
            self.brush_keys.clear()
            self.brush_offsets.clear()
            self.dirty = False
            return

        # Collect geometry from all brushes
        all_vertices = []
        all_indices = []
        vertex_offset = 0

        self.brush_keys.clear()
        self.brush_offsets.clear()

        for brush, brush_key in brush_data:
            brush_vertices, brush_indices = self._extract_brush_geometry(brush, vertex_offset)

            if brush_vertices is not None and len(brush_vertices) > 0:
                self.brush_offsets[brush_key] = (len(all_vertices), len(all_indices))
                all_vertices.extend(brush_vertices)
                all_indices.extend(brush_indices)
                self.brush_keys.add(brush_key)
                vertex_offset += len(brush_vertices) // 8  # 8 floats per vertex

        if not all_vertices:
            self.release()
            self.vertex_count = 0
            self.index_count = 0
            self.dirty = False
            return

        # Convert to numpy arrays
        vertices_array = np.array(all_vertices, dtype='f4')
        indices_array = np.array(all_indices, dtype='i4')

        self.vertex_count = len(vertices_array) // 8
        self.index_count = len(indices_array)

        # Create or update buffers
        self._update_buffers(vertices_array, indices_array)
        self.dirty = False

    def _extract_brush_geometry(
        self, brush: "Brush", vertex_offset: int
    ) -> tuple[list[float], list[int]] | tuple[None, None]:
        """
        Extract vertex and index data from a brush.

        Args:
            brush: Brush to extract geometry from
            vertex_offset: Current vertex offset for index adjustment

        Returns:
            Tuple of (vertices, indices) or (None, None) if invalid
        """
        import math

        # Compute face vertices from planes
        face_vertices = compute_brush_vertices(brush)

        vertices = []
        indices = []
        local_vertex_index = 0

        for face_idx, face_verts in face_vertices.items():
            if len(face_verts) < 3:
                continue

            plane = brush.planes[face_idx]
            normal = plane.normal

            # Validate normal - Vec3 check
            if math.isnan(normal.x) or math.isnan(normal.y) or math.isnan(normal.z):
                continue
            if math.isinf(normal.x) or math.isinf(normal.y) or math.isinf(normal.z):
                continue

            # MAP normals point inward, negate for outward-facing (required for lighting)
            # But keep original for UV calculation (matches MAP editor behavior)
            normal_arr = np.array([normal.x, normal.y, normal.z], dtype=np.float64)
            out_normal = np.array([-normal.x, -normal.y, -normal.z], dtype=np.float64)

            # Store first vertex index for this face
            first_vertex_index = local_vertex_index

            for vertex in face_verts:
                # Validate vertex - Vec3 check
                if math.isnan(vertex.x) or math.isnan(vertex.y) or math.isnan(vertex.z):
                    continue
                if math.isinf(vertex.x) or math.isinf(vertex.y) or math.isinf(vertex.z):
                    continue

                # Convert vertex to numpy for compute_uv
                vertex_arr = np.array([vertex.x, vertex.y, vertex.z], dtype=np.float64)

                # Compute UV coordinates using original normal (matches Radiant editor)
                # Note: Single-texture mode uses default 256x256 dimensions
                # For proper UV mapping, use multi-texture mode (use_per_face_textures=True)
                u, v = compute_uv(
                    vertex_arr,
                    normal_arr,
                    (plane.texture.offset_x, plane.texture.offset_y),
                    plane.texture.rotation,
                    (plane.texture.scale_x, plane.texture.scale_y),
                )

                # Position (3), Normal (3), TexCoord (2) = 8 floats
                # Use outward-facing normal for correct lighting
                vertices.extend([
                    float(vertex.x), float(vertex.y), float(vertex.z),
                    float(out_normal[0]), float(out_normal[1]), float(out_normal[2]),
                    float(u), float(v)
                ])
                local_vertex_index += 1

            # Vertices are sorted clockwise from inside (= CCW from outside)
            # Standard triangle fan with CCW winding
            num_face_verts = local_vertex_index - first_vertex_index
            for i in range(1, num_face_verts - 1):
                indices.extend([
                    vertex_offset + first_vertex_index,
                    vertex_offset + first_vertex_index + i,
                    vertex_offset + first_vertex_index + i + 1
                ])

        if not vertices or not indices:
            return None, None

        return vertices, indices

    def _update_buffers(self, vertices: np.ndarray, indices: np.ndarray):
        """Create or update GPU buffers."""
        # Release old buffers
        self.release()

        # Create new buffers
        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.ibo = self.ctx.buffer(indices.tobytes())

        # Create VAO
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
            self.ibo
        )

    def render(self):
        """Render the batch."""
        if self.vao and self.index_count > 0:
            self.vao.render()

    def is_empty(self) -> bool:
        """Check if batch has no geometry."""
        return self.index_count == 0


class WireframeBatch:
    """
    A batch for wireframe rendering with face normals for backface culling.

    Uses (entity_idx, brush_idx) tuples as brush keys.
    """

    __slots__ = (
        'ctx', 'program', 'vao', 'vbo',
        'vertex_count', 'brush_keys', 'dirty'
    )

    def __init__(self, ctx: "moderngl.Context", program: "moderngl.Program"):
        self.ctx = ctx
        self.program = program

        self.vao: "moderngl.VertexArray | None" = None
        self.vbo: "moderngl.Buffer | None" = None

        self.vertex_count = 0
        self.brush_keys: set[tuple[int, int]] = set()
        self.dirty = True

    def release(self):
        """Release GPU resources."""
        if self.vao:
            self.vao.release()
            self.vao = None
        if self.vbo:
            self.vbo.release()
            self.vbo = None

    def build(self, brush_data: list[tuple["Brush", tuple[int, int]]]):
        """Build wireframe batch from brushes with their keys."""
        if not brush_data:
            self.release()
            self.vertex_count = 0
            self.brush_keys.clear()
            self.dirty = False
            return

        all_vertices = []
        self.brush_keys.clear()

        for brush, brush_key in brush_data:
            brush_verts = self._extract_wireframe_geometry(brush)
            if brush_verts:
                all_vertices.extend(brush_verts)
                self.brush_keys.add(brush_key)

        if not all_vertices:
            self.release()
            self.vertex_count = 0
            self.dirty = False
            return

        vertices_array = np.array(all_vertices, dtype='f4')
        self.vertex_count = len(vertices_array) // 6  # 6 floats per vertex (pos + normal)

        self._update_buffers(vertices_array)
        self.dirty = False

    def _extract_wireframe_geometry(self, brush: "Brush") -> list[float]:
        """Extract wireframe line vertices with face normals."""
        import math

        # Compute face vertices from planes
        face_vertices = compute_brush_vertices(brush)

        vertices = []

        for face_idx, face_verts in face_vertices.items():
            if len(face_verts) < 3:
                continue

            plane = brush.planes[face_idx]
            normal = plane.normal

            # Validate normal
            if math.isnan(normal.x) or math.isnan(normal.y) or math.isnan(normal.z):
                # Fallback normal calculation
                v0, v1, v2 = face_verts[0], face_verts[1], face_verts[2]
                edge1 = v1 - v0
                edge2 = v2 - v0
                normal = edge1.cross(edge2).normalize()
                if math.isnan(normal.x):
                    from ..core import Vec3
                    normal = Vec3(0, 0, 1)

            # Negate normal for outward-facing direction (MAP normals point inward)
            nx, ny, nz = -normal.x, -normal.y, -normal.z

            # Draw edges with face normal
            for i in range(len(face_verts)):
                v1 = face_verts[i]
                v2 = face_verts[(i + 1) % len(face_verts)]

                # Validate vertices
                if math.isnan(v1.x) or math.isinf(v1.x):
                    continue
                if math.isnan(v2.x) or math.isinf(v2.x):
                    continue

                # Line vertex 1: position + negated normal (outward-facing)
                vertices.extend([
                    float(v1.x), float(v1.y), float(v1.z),
                    float(nx), float(ny), float(nz)
                ])
                # Line vertex 2: position + negated normal (outward-facing)
                vertices.extend([
                    float(v2.x), float(v2.y), float(v2.z),
                    float(nx), float(ny), float(nz)
                ])

        return vertices

    def _update_buffers(self, vertices: np.ndarray):
        """Create or update GPU buffers."""
        self.release()

        self.vbo = self.ctx.buffer(vertices.tobytes())
        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f', 'in_position', 'in_normal')]
        )

    def render(self, mode=None):
        """Render the wireframe batch as lines."""
        if self.vao and self.vertex_count > 0:
            import moderngl
            self.vao.render(moderngl.LINES)

    def is_empty(self) -> bool:
        return self.vertex_count == 0


class TextureBatch:
    """
    A batch for a single texture containing all faces using that texture.

    This is used for multi-texture rendering where faces are grouped
    by their shader/texture name.
    """

    __slots__ = (
        'ctx', 'program', 'vao', 'vbo', 'ibo',
        'texture_name', 'vertex_count', 'index_count'
    )

    def __init__(self, ctx: "moderngl.Context", program: "moderngl.Program", texture_name: str):
        self.ctx = ctx
        self.program = program
        self.texture_name = texture_name

        self.vao: "moderngl.VertexArray | None" = None
        self.vbo: "moderngl.Buffer | None" = None
        self.ibo: "moderngl.Buffer | None" = None

        self.vertex_count = 0
        self.index_count = 0

    def release(self):
        """Release GPU resources."""
        if self.vao:
            self.vao.release()
            self.vao = None
        if self.vbo:
            self.vbo.release()
            self.vbo = None
        if self.ibo:
            self.ibo.release()
            self.ibo = None

    def build(self, vertices: list[float], indices: list[int]):
        """Build the batch from vertex and index data."""
        if not vertices or not indices:
            self.release()
            self.vertex_count = 0
            self.index_count = 0
            return

        vertices_array = np.array(vertices, dtype='f4')
        indices_array = np.array(indices, dtype='i4')

        self.vertex_count = len(vertices_array) // 8  # 8 floats per vertex
        self.index_count = len(indices_array)

        self.release()

        self.vbo = self.ctx.buffer(vertices_array.tobytes())
        self.ibo = self.ctx.buffer(indices_array.tobytes())

        self.vao = self.ctx.vertex_array(
            self.program,
            [(self.vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')],
            self.ibo
        )

    def render(self):
        """Render this texture batch."""
        if self.vao and self.index_count > 0:
            self.vao.render()

    def is_empty(self) -> bool:
        return self.index_count == 0


class TexturedBatchGroup:
    """
    Manages multiple TextureBatch objects, one per unique texture.

    This enables efficient multi-texture rendering by grouping faces
    by their shader name and rendering each group with its GPU texture bound.
    """

    __slots__ = (
        'ctx', 'program', 'batches', '_gpu_textures', '_default_texture'
    )

    def __init__(self, ctx: "moderngl.Context", program: "moderngl.Program"):
        self.ctx = ctx
        self.program = program

        # texture_name -> TextureBatch
        self.batches: dict[str, TextureBatch] = {}

        # texture_name -> moderngl.Texture (cached GPU textures)
        self._gpu_textures: dict[str, "moderngl.Texture"] = {}

        # Fallback texture for missing textures
        self._default_texture: "moderngl.Texture | None" = None

    def release(self):
        """Release all GPU resources."""
        for batch in self.batches.values():
            batch.release()
        self.batches.clear()

        # Note: GPU textures are managed by TextureManager, don't release here
        self._gpu_textures.clear()

    def set_default_texture(self, texture: "moderngl.Texture | None"):
        """Set the fallback texture for faces with missing textures."""
        self._default_texture = texture

    def build(self, face_data_by_texture: dict[str, tuple[list[float], list[int]]]):
        """
        Build batches from face data grouped by texture.

        Args:
            face_data_by_texture: Dict mapping texture_name -> (vertices, indices)
        """
        # Release old batches for textures no longer used
        old_textures = set(self.batches.keys())
        new_textures = set(face_data_by_texture.keys())

        for old_tex in old_textures - new_textures:
            self.batches[old_tex].release()
            del self.batches[old_tex]

        # Build/update batches
        for texture_name, (vertices, indices) in face_data_by_texture.items():
            if texture_name not in self.batches:
                self.batches[texture_name] = TextureBatch(self.ctx, self.program, texture_name)
            self.batches[texture_name].build(vertices, indices)

    def get_gpu_texture(self, texture_name: str) -> "moderngl.Texture | None":
        """Get GPU texture for a texture name, loading if necessary."""
        # Check cache first
        if texture_name in self._gpu_textures:
            return self._gpu_textures[texture_name]

        # Try to load from TextureManager
        texture_manager = get_texture_manager()
        gpu_tex = texture_manager.get_gpu_texture(self.ctx, texture_name)

        if gpu_tex is not None:
            self._gpu_textures[texture_name] = gpu_tex
            return gpu_tex

        # Return default texture as fallback
        return self._default_texture

    def render(self, use_textures: bool = True):
        """
        Render all texture batches.

        Args:
            use_textures: If True, bind GPU textures; if False, use solid color
        """
        for texture_name, batch in self.batches.items():
            if batch.is_empty():
                continue

            if use_textures:
                # Bind the texture for this batch
                gpu_tex = self.get_gpu_texture(texture_name)
                if gpu_tex is not None:
                    gpu_tex.use(location=0)
                    self.program['u_use_texture'].value = True
                else:
                    self.program['u_use_texture'].value = False
            else:
                self.program['u_use_texture'].value = False

            batch.render()

    def get_stats(self) -> dict:
        """Get statistics about texture batches."""
        total_vertices = sum(b.vertex_count for b in self.batches.values())
        total_indices = sum(b.index_count for b in self.batches.values())
        return {
            'texture_count': len(self.batches),
            'total_vertices': total_vertices,
            'total_indices': total_indices,
            'cached_gpu_textures': len(self._gpu_textures),
        }

    def is_empty(self) -> bool:
        return len(self.batches) == 0 or all(b.is_empty() for b in self.batches.values())


class BatchedBrushRenderer:
    """
    High-level manager for batched brush rendering.

    Maintains separate batches for:
    - Unselected brushes (static, rarely changes)
    - Selected brushes (dynamic, changes with selection)

    This allows efficient updates when selection changes without
    rebuilding the entire scene.

    Uses (entity_idx, brush_idx) tuples as brush keys.
    """

    __slots__ = (
        'ctx', 'brush_program', 'wireframe_program',
        'unselected_batch', 'selected_batch',
        'unselected_wireframe', 'selected_wireframe',
        'unselected_textured', 'selected_textured',
        '_all_brushes', '_selected_keys', '_filtered_keys',
        '_enabled', '_needs_full_rebuild', '_needs_selection_update', '_needs_filter_rebuild',
        '_default_texture'
    )

    def __init__(
        self,
        ctx: "moderngl.Context",
        brush_program: "moderngl.Program",
        wireframe_program: "moderngl.Program"
    ):
        self.ctx = ctx
        self.brush_program = brush_program
        self.wireframe_program = wireframe_program

        # Solid geometry batches (single-texture mode)
        self.unselected_batch = BrushBatch(ctx, brush_program)
        self.selected_batch = BrushBatch(ctx, brush_program)

        # Wireframe batches
        self.unselected_wireframe = WireframeBatch(ctx, wireframe_program)
        self.selected_wireframe = WireframeBatch(ctx, wireframe_program)

        # Multi-texture batch groups (per-face texturing)
        self.unselected_textured = TexturedBatchGroup(ctx, brush_program)
        self.selected_textured = TexturedBatchGroup(ctx, brush_program)

        # State tracking - list of (Brush, brush_key) tuples
        self._all_brushes: list[tuple["Brush", tuple[int, int]]] = []
        self._selected_keys: set[tuple[int, int]] = set()
        self._filtered_keys: set[tuple[int, int]] | None = None  # None = show all, set = only these
        self._enabled = True
        self._needs_full_rebuild = True
        self._needs_selection_update = False
        self._needs_filter_rebuild = False

        # Default texture for faces without valid textures
        self._default_texture: "moderngl.Texture | None" = None

    def release(self):
        """Release all GPU resources."""
        self.unselected_batch.release()
        self.selected_batch.release()
        self.unselected_wireframe.release()
        self.selected_wireframe.release()
        self.unselected_textured.release()
        self.selected_textured.release()

    def set_default_texture(self, texture: "moderngl.Texture | None"):
        """Set the default/fallback texture for faces with missing textures."""
        self._default_texture = texture
        self.unselected_textured.set_default_texture(texture)
        self.selected_textured.set_default_texture(texture)

    def set_enabled(self, enabled: bool):
        """Enable or disable batched rendering."""
        self._enabled = enabled

    def is_enabled(self) -> bool:
        return self._enabled

    def set_brushes(
        self,
        brush_data: list[tuple["Brush", tuple[int, int]]],
        progress_callback: Callable[[int, int], None] | None = None
    ):
        """
        Set the full list of brushes to render.

        Args:
            brush_data: List of (Brush, brush_key) tuples where brush_key is (entity_idx, brush_idx)
            progress_callback: Optional progress callback(current, total)
        """
        self._all_brushes = list(brush_data)
        self._needs_full_rebuild = True

        if progress_callback:
            progress_callback(0, len(brush_data))

    def update_selection(self, selected_keys: set[tuple[int, int]]):
        """
        Update which brushes are selected.

        This triggers a partial rebuild - only the selected/unselected
        batches need to be updated, not the geometry itself.

        Args:
            selected_keys: Set of (entity_idx, brush_idx) tuples for selected brushes
        """
        if selected_keys != self._selected_keys:
            self._selected_keys = set(selected_keys)
            self._needs_selection_update = True

    def set_filtered_brush_keys(self, filtered_keys: set[tuple[int, int]] | None):
        """
        Set which brushes pass the visibility filter.

        When filters are active, only brushes in filtered_keys will be rendered.
        The batches are rebuilt to contain only the filtered brushes.

        Args:
            filtered_keys: Set of (entity_idx, brush_idx) tuples that pass the filter, or None to show all
        """
        # Check if filter actually changed
        if filtered_keys == self._filtered_keys:
            return
        if filtered_keys is not None and self._filtered_keys is not None:
            if filtered_keys == self._filtered_keys:
                return

        self._filtered_keys = set(filtered_keys) if filtered_keys is not None else None
        self._needs_filter_rebuild = True

    def update_brush(self, brush: "Brush", brush_key: tuple[int, int]):
        """
        Update a single brush's geometry (e.g., after movement).

        For now, this triggers a full rebuild of the affected batch.
        Future optimization: implement partial buffer updates.

        Args:
            brush: The updated Brush object
            brush_key: The (entity_idx, brush_idx) tuple identifying the brush
        """
        # Mark for rebuild
        if brush_key in self._selected_keys:
            self.selected_batch.dirty = True
            self.selected_wireframe.dirty = True
        else:
            self.unselected_batch.dirty = True
            self.unselected_wireframe.dirty = True

        # Update brush in list
        for i, (b, key) in enumerate(self._all_brushes):
            if key == brush_key:
                self._all_brushes[i] = (brush, brush_key)
                break

        self._needs_selection_update = True

    def rebuild_if_needed(self):
        """Rebuild batches if necessary."""
        if not self._enabled:
            return

        if self._needs_full_rebuild:
            self._rebuild_all()
            self._needs_full_rebuild = False
            self._needs_selection_update = False
            self._needs_filter_rebuild = False
        elif self._needs_filter_rebuild:
            self._rebuild_all()  # Filter change requires full rebuild
            self._needs_filter_rebuild = False
            self._needs_selection_update = False
        elif self._needs_selection_update:
            self._rebuild_by_selection()
            self._needs_selection_update = False

    def _rebuild_all(self):
        """Full rebuild of all batches."""
        selected_brush_data: list[tuple["Brush", tuple[int, int]]] = []
        unselected_brush_data: list[tuple["Brush", tuple[int, int]]] = []

        for brush, brush_key in self._all_brushes:
            # Skip brushes not passing filter (if filter is active)
            if self._filtered_keys is not None and brush_key not in self._filtered_keys:
                continue

            if brush_key in self._selected_keys:
                selected_brush_data.append((brush, brush_key))
            else:
                unselected_brush_data.append((brush, brush_key))

        # Build solid batches (single-texture mode, only filtered brushes)
        self.unselected_batch.build(unselected_brush_data)
        self.selected_batch.build(selected_brush_data)

        # Build wireframe batches
        self.unselected_wireframe.build(unselected_brush_data)
        self.selected_wireframe.build(selected_brush_data)

        # Build multi-texture batches (per-face texturing)
        unselected_by_texture = self._extract_faces_by_texture(unselected_brush_data)
        selected_by_texture = self._extract_faces_by_texture(selected_brush_data)

        self.unselected_textured.build(unselected_by_texture)
        self.selected_textured.build(selected_by_texture)

    def _extract_faces_by_texture(
        self,
        brush_data: list[tuple["Brush", tuple[int, int]]]
    ) -> dict[str, tuple[list[float], list[int]]]:
        """
        Extract face geometry grouped by texture name.

        Args:
            brush_data: List of (Brush, brush_key) tuples

        Returns:
            Dict mapping texture_name -> (vertices, indices)
        """
        import math

        # texture_name -> (vertices list, indices list, current vertex offset)
        texture_groups: dict[str, tuple[list[float], list[int], int]] = {}

        # Cache for texture dimensions to avoid repeated lookups
        texture_dimensions: dict[str, tuple[int, int]] = {}
        texture_manager = get_texture_manager()

        for brush, brush_key in brush_data:
            # Compute face vertices from planes
            face_vertices = compute_brush_vertices(brush)

            for face_idx, face_verts in face_vertices.items():
                if len(face_verts) < 3:
                    continue

                plane = brush.planes[face_idx]
                texture_name = plane.shader
                normal = plane.normal

                # Validate normal
                if math.isnan(normal.x) or math.isnan(normal.y) or math.isnan(normal.z):
                    continue
                if math.isinf(normal.x) or math.isinf(normal.y) or math.isinf(normal.z):
                    continue

                # Get texture dimensions (cached)
                if texture_name not in texture_dimensions:
                    tex_info = texture_manager.get_texture_info(texture_name)
                    if tex_info and tex_info.width > 0 and tex_info.height > 0:
                        texture_dimensions[texture_name] = (tex_info.width, tex_info.height)
                    else:
                        # Load texture to get dimensions if not cached
                        tex_info = texture_manager.get_texture_info(texture_name)
                        if tex_info:
                            # Force load to get dimensions
                            texture_manager._load_image(texture_name)
                            tex_info = texture_manager.get_texture_info(texture_name)
                            if tex_info and tex_info.width > 0:
                                texture_dimensions[texture_name] = (tex_info.width, tex_info.height)
                            else:
                                texture_dimensions[texture_name] = (256, 256)
                        else:
                            texture_dimensions[texture_name] = (256, 256)

                tex_width, tex_height = texture_dimensions[texture_name]

                # Initialize texture group if needed
                if texture_name not in texture_groups:
                    texture_groups[texture_name] = ([], [], 0)

                vertices, indices, vertex_offset = texture_groups[texture_name]

                # MAP normals point inward, negate for outward-facing (required for lighting)
                # But keep original for UV calculation (matches MAP editor behavior)
                normal_arr = np.array([normal.x, normal.y, normal.z], dtype=np.float64)
                out_normal = np.array([-normal.x, -normal.y, -normal.z], dtype=np.float64)

                first_vertex_index = vertex_offset

                for vertex in face_verts:
                    # Validate vertex
                    if math.isnan(vertex.x) or math.isnan(vertex.y) or math.isnan(vertex.z):
                        continue
                    if math.isinf(vertex.x) or math.isinf(vertex.y) or math.isinf(vertex.z):
                        continue

                    # Convert vertex to numpy for compute_uv
                    vertex_arr = np.array([vertex.x, vertex.y, vertex.z], dtype=np.float64)

                    # Compute UV coordinates using original normal (matches Radiant editor)
                    u, v = compute_uv(
                        vertex_arr,
                        normal_arr,
                        (plane.texture.offset_x, plane.texture.offset_y),
                        plane.texture.rotation,
                        (plane.texture.scale_x, plane.texture.scale_y),
                        texture_width=tex_width,
                        texture_height=tex_height,
                    )

                    # Position (3), Normal (3), TexCoord (2) = 8 floats
                    # Use outward-facing normal for correct lighting
                    vertices.extend([
                        float(vertex.x), float(vertex.y), float(vertex.z),
                        float(out_normal[0]), float(out_normal[1]), float(out_normal[2]),
                        float(u), float(v)
                    ])
                    vertex_offset += 1

                # Vertices are sorted clockwise from inside (= CCW from outside)
                # Standard triangle fan with CCW winding
                num_face_verts = vertex_offset - first_vertex_index
                for i in range(1, num_face_verts - 1):
                    indices.extend([
                        first_vertex_index,
                        first_vertex_index + i,
                        first_vertex_index + i + 1
                    ])

                # Update the tuple with new vertex offset
                texture_groups[texture_name] = (vertices, indices, vertex_offset)

        # Convert to final format (drop the vertex offset)
        result: dict[str, tuple[list[float], list[int]]] = {}
        for texture_name, (vertices, indices, _) in texture_groups.items():
            if vertices and indices:
                result[texture_name] = (vertices, indices)

        return result

    def _rebuild_by_selection(self):
        """Rebuild batches based on selection change."""
        # Same as full rebuild for now
        # Future optimization: only rebuild changed brushes
        self._rebuild_all()

    def render_solid(
        self,
        mvp: np.ndarray,
        model: np.ndarray,
        base_color: tuple[float, float, float],
        selection_color: tuple[float, float, float] | None = None,
        use_textures: bool = False,
        texture: "moderngl.Texture | None" = None,
        use_per_face_textures: bool = False,
    ):
        """
        Render solid brush geometry.

        Args:
            mvp: Model-View-Projection matrix
            model: Model matrix
            base_color: Color for unselected brushes
            selection_color: Color for selected brushes (defaults to base_color)
            use_textures: Whether to use texture mapping
            texture: Optional texture to bind (single-texture mode)
            use_per_face_textures: If True, use multi-texture mode with per-face textures
        """
        if not self._enabled:
            return

        self.rebuild_if_needed()

        self.brush_program['u_mvp'].write(mvp.tobytes())
        self.brush_program['u_model'].write(model.tobytes())
        self.brush_program['u_light_dir'].value = (0.5, 0.3, 1.0)

        if 'u_texture' in self.brush_program:
            self.brush_program['u_texture'].value = 0

        # Multi-texture mode: render per-face textures
        if use_textures and use_per_face_textures:
            self._render_solid_multi_texture(base_color, selection_color)
        else:
            # Single-texture mode (legacy)
            self._render_solid_single_texture(base_color, selection_color, use_textures, texture)

    def _render_solid_single_texture(
        self,
        base_color: tuple[float, float, float],
        selection_color: tuple[float, float, float] | None,
        use_textures: bool,
        texture: "moderngl.Texture | None",
    ):
        """Render using single-texture mode (all faces same texture)."""
        self.brush_program['u_use_texture'].value = use_textures and texture is not None

        # Bind texture if provided
        if use_textures and texture is not None:
            texture.use(location=0)

        # Render unselected brushes
        if not self.unselected_batch.is_empty():
            self.brush_program['u_selected'].value = False
            self.brush_program['u_color'].value = base_color
            self.unselected_batch.render()

        # Render selected brushes
        if not self.selected_batch.is_empty():
            self.brush_program['u_selected'].value = True
            self.brush_program['u_color'].value = selection_color or base_color
            self.selected_batch.render()

    def _render_solid_multi_texture(
        self,
        base_color: tuple[float, float, float],
        selection_color: tuple[float, float, float] | None,
    ):
        """Render using multi-texture mode (per-face textures)."""
        # Render unselected brushes with per-face textures
        if not self.unselected_textured.is_empty():
            self.brush_program['u_selected'].value = False
            self.brush_program['u_color'].value = base_color
            self.unselected_textured.render(use_textures=True)

        # Render selected brushes with per-face textures
        if not self.selected_textured.is_empty():
            self.brush_program['u_selected'].value = True
            self.brush_program['u_color'].value = selection_color or base_color
            self.selected_textured.render(use_textures=True)

    def render_wireframe(
        self,
        mvp: np.ndarray,
        camera_pos: tuple[float, float, float],
        outline_color: tuple[float, float, float, float],
        selection_color: tuple[float, float, float, float],
        backface_culling: bool = True
    ):
        """
        Render wireframe overlay.

        Args:
            mvp: Model-View-Projection matrix
            camera_pos: Camera position for backface culling
            outline_color: Color for unselected brush wireframes
            selection_color: Color for selected brush wireframes
            backface_culling: Whether to enable backface culling
        """
        if not self._enabled:
            return

        self.rebuild_if_needed()

        self.wireframe_program['u_mvp'].write(mvp.tobytes())
        self.wireframe_program['u_camera_pos'].value = camera_pos
        self.wireframe_program['u_backface_culling'].value = 1 if backface_culling else 0

        # Render unselected wireframes
        if not self.unselected_wireframe.is_empty():
            self.wireframe_program['u_color'].value = outline_color
            self.unselected_wireframe.render()

        # Render selected wireframes
        if not self.selected_wireframe.is_empty():
            self.wireframe_program['u_color'].value = selection_color
            self.selected_wireframe.render()

    def get_stats(self) -> dict:
        """Get rendering statistics."""
        visible_count = len(self._filtered_keys) if self._filtered_keys is not None else len(self._all_brushes)

        # Count texture batches for draw call estimation
        unselected_tex_stats = self.unselected_textured.get_stats()
        selected_tex_stats = self.selected_textured.get_stats()
        texture_draw_calls = unselected_tex_stats['texture_count'] + selected_tex_stats['texture_count']

        return {
            'total_brushes': len(self._all_brushes),
            'visible_brushes': visible_count,
            'filtered': self._filtered_keys is not None,
            'selected_brushes': len(self._selected_keys),
            'unselected_vertices': self.unselected_batch.vertex_count,
            'selected_vertices': self.selected_batch.vertex_count,
            'unselected_indices': self.unselected_batch.index_count,
            'selected_indices': self.selected_batch.index_count,
            'draw_calls': 4 if self._enabled else len(self._all_brushes) * 2,
            'texture_count': unselected_tex_stats['texture_count'] + selected_tex_stats['texture_count'],
            'texture_draw_calls': texture_draw_calls + 2,  # +2 for wireframe
            'cached_gpu_textures': unselected_tex_stats['cached_gpu_textures'],
        }
