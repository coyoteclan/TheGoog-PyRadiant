"""Instanced rendering for efficient drawing of repeated geometry."""

from __future__ import annotations

from enum import IntEnum
from pathlib import Path
from typing import TYPE_CHECKING
import numpy as np

if TYPE_CHECKING:
    import moderngl
    from ..core import Entity


class MarkerShape(IntEnum):
    """Shape types for entity markers."""
    SQUARE = 0
    CIRCLE = 1
    DIAMOND = 2
    CROSS = 3


# Default colors for different entity types
ENTITY_COLORS = {
    'light': (1.0, 1.0, 0.3, 1.0),           # Yellow
    'light_spot': (1.0, 0.8, 0.2, 1.0),      # Orange-yellow
    'info_player_start': (0.2, 1.0, 0.2, 1.0),  # Green
    'info_player_deathmatch': (0.2, 0.8, 1.0, 1.0),  # Cyan
    'mp_teamdeathmatch_spawn': (0.2, 0.6, 1.0, 1.0),  # Blue
    'mp_searchanddestroy_spawn_axis': (1.0, 0.3, 0.3, 1.0),  # Red
    'mp_searchanddestroy_spawn_allies': (0.3, 0.3, 1.0, 1.0),  # Blue
    'trigger': (1.0, 0.5, 0.0, 0.5),         # Orange (semi-transparent)
    'script_model': (0.8, 0.4, 1.0, 1.0),    # Purple
    'misc_model': (0.8, 0.4, 1.0, 1.0),      # Purple
    'default': (0.7, 0.7, 0.7, 1.0),         # Gray
}


def get_entity_color(classname: str) -> tuple[float, float, float, float]:
    """Get color for an entity based on its classname."""
    # Check exact match first
    if classname in ENTITY_COLORS:
        return ENTITY_COLORS[classname]

    # Check prefix matches
    for prefix, color in ENTITY_COLORS.items():
        if classname.startswith(prefix):
            return color

    return ENTITY_COLORS['default']


def get_entity_shape(classname: str) -> MarkerShape:
    """Get marker shape for an entity based on its classname."""
    if classname.startswith('light'):
        return MarkerShape.DIAMOND
    elif classname.startswith('info_player') or 'spawn' in classname:
        return MarkerShape.CROSS
    elif classname.startswith('trigger'):
        return MarkerShape.SQUARE
    else:
        return MarkerShape.CIRCLE


class InstancedMarkerRenderer:
    """
    Renders entity markers using GPU instancing.

    Instead of drawing each marker with a separate draw call,
    this batches all markers into a single instanced draw call.
    """

    __slots__ = (
        'ctx', 'program', 'quad_vao', 'quad_vbo',
        'instance_vbo', 'instance_count', 'instance_capacity',
        '_enabled', '_marker_size', '_needs_rebuild'
    )

    # Unit quad vertices (two triangles)
    QUAD_VERTICES = np.array([
        -0.5, -0.5,
         0.5, -0.5,
         0.5,  0.5,
        -0.5, -0.5,
         0.5,  0.5,
        -0.5,  0.5,
    ], dtype='f4')

    def __init__(self, ctx: "moderngl.Context", initial_capacity: int = 1000):
        """
        Initialize the instanced marker renderer.

        Args:
            ctx: ModernGL context
            initial_capacity: Initial instance buffer capacity
        """
        self.ctx = ctx
        self.program: "moderngl.Program | None" = None
        self.quad_vao: "moderngl.VertexArray | None" = None
        self.quad_vbo: "moderngl.Buffer | None" = None
        self.instance_vbo: "moderngl.Buffer | None" = None

        self.instance_count = 0
        self.instance_capacity = initial_capacity

        self._enabled = True
        self._marker_size = 16.0  # Default marker size in world units
        self._needs_rebuild = True

        self._init_shaders()
        self._init_buffers()

    def _init_shaders(self):
        """Load and compile instanced marker shaders."""
        shader_dir = Path(__file__).parent / "shaders"

        vert_src = (shader_dir / "instanced_marker.vert").read_text()
        frag_src = (shader_dir / "instanced_marker.frag").read_text()

        self.program = self.ctx.program(
            vertex_shader=vert_src,
            fragment_shader=frag_src
        )

    def _init_buffers(self):
        """Initialize GPU buffers."""
        # Quad vertex buffer (shared geometry)
        self.quad_vbo = self.ctx.buffer(self.QUAD_VERTICES.tobytes())

        # Instance data buffer
        # Each instance: position (3f) + color (4f) + size (1f) = 8 floats = 32 bytes
        instance_data = np.zeros(self.instance_capacity * 8, dtype='f4')
        self.instance_vbo = self.ctx.buffer(instance_data.tobytes(), dynamic=True)

        # Create VAO with instanced attributes
        self.quad_vao = self.ctx.vertex_array(
            self.program,
            [
                # Per-vertex data (quad)
                (self.quad_vbo, '2f', 'in_vertex'),
                # Per-instance data
                (self.instance_vbo, '3f 4f 1f /i', 'in_position', 'in_color', 'in_size'),
            ]
        )

    def release(self):
        """Release GPU resources."""
        if self.quad_vao:
            self.quad_vao.release()
            self.quad_vao = None
        if self.quad_vbo:
            self.quad_vbo.release()
            self.quad_vbo = None
        if self.instance_vbo:
            self.instance_vbo.release()
            self.instance_vbo = None
        if self.program:
            self.program.release()
            self.program = None

    def set_enabled(self, enabled: bool):
        """Enable or disable instanced rendering."""
        self._enabled = enabled

    def set_marker_size(self, size: float):
        """Set the default marker size."""
        self._marker_size = size

    def update_entities(self, entities: list["Entity"]):
        """
        Update instance data from entity list.

        Args:
            entities: List of Entity objects to render as markers
        """
        # Filter to only point entities (have origin, no brushes)
        point_entities = [e for e in entities if e.is_point_entity]

        if not point_entities:
            self.instance_count = 0
            return

        # Grow buffer if needed
        if len(point_entities) > self.instance_capacity:
            self._resize_instance_buffer(len(point_entities) * 2)

        # Build instance data
        instance_data = []
        for entity in point_entities:
            origin = entity.origin
            if origin is None:
                continue

            color = get_entity_color(entity.classname)
            size = self._marker_size

            # Pack: position (3f) + color (4f) + size (1f)
            instance_data.extend([
                float(origin.x), float(origin.y), float(origin.z),
                color[0], color[1], color[2], color[3],
                size
            ])

        if instance_data:
            data_array = np.array(instance_data, dtype='f4')
            self.instance_vbo.write(data_array.tobytes())
            self.instance_count = len(point_entities)
        else:
            self.instance_count = 0

    def _resize_instance_buffer(self, new_capacity: int):
        """Resize the instance buffer."""
        if self.instance_vbo:
            self.instance_vbo.release()

        self.instance_capacity = new_capacity
        instance_data = np.zeros(new_capacity * 8, dtype='f4')
        self.instance_vbo = self.ctx.buffer(instance_data.tobytes(), dynamic=True)

        # Recreate VAO with new buffer
        if self.quad_vao:
            self.quad_vao.release()

        self.quad_vao = self.ctx.vertex_array(
            self.program,
            [
                (self.quad_vbo, '2f', 'in_vertex'),
                (self.instance_vbo, '3f 4f 1f /i', 'in_position', 'in_color', 'in_size'),
            ]
        )

    def render(
        self,
        view_matrix: np.ndarray,
        projection_matrix: np.ndarray,
        camera_right: np.ndarray,
        camera_up: np.ndarray,
        shape: MarkerShape = MarkerShape.CIRCLE
    ):
        """
        Render all entity markers in a single draw call.

        Args:
            view_matrix: View matrix (4x4)
            projection_matrix: Projection matrix (4x4)
            camera_right: Camera right vector for billboarding
            camera_up: Camera up vector for billboarding
            shape: Marker shape to use
        """
        if not self._enabled or self.instance_count == 0:
            return

        if self.program is None or self.quad_vao is None:
            return

        # Set uniforms
        self.program['u_view'].write(view_matrix.T.astype('f4').tobytes())
        self.program['u_projection'].write(projection_matrix.T.astype('f4').tobytes())
        self.program['u_camera_right'].value = (
            float(camera_right[0]),
            float(camera_right[1]),
            float(camera_right[2])
        )
        self.program['u_camera_up'].value = (
            float(camera_up[0]),
            float(camera_up[1]),
            float(camera_up[2])
        )
        self.program['u_shape'].value = int(shape)

        # Enable blending for transparency
        self.ctx.enable(self.ctx.BLEND)
        self.ctx.blend_func = self.ctx.SRC_ALPHA, self.ctx.ONE_MINUS_SRC_ALPHA

        # Disable depth write but keep depth test
        # This allows markers to be occluded by geometry but not write to depth
        self.ctx.depth_func = '<='

        # Render all instances in one call!
        self.quad_vao.render(instances=self.instance_count)

        # Restore state
        self.ctx.depth_func = '<'
        self.ctx.disable(self.ctx.BLEND)

    def get_stats(self) -> dict:
        """Get rendering statistics."""
        return {
            'entity_count': self.instance_count,
            'buffer_capacity': self.instance_capacity,
            'enabled': self._enabled,
            'marker_size': self._marker_size,
        }
