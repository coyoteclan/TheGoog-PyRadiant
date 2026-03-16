"""
Primitive brush generators (cylinder, cone, wedge, spike).

Creates brush primitives using the new parser classes (Vec3-based).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..io.map_parser import Brush, BrushPlane, create_brush_box
from ..io.map_parser.math import Vec3
from ..io.map_parser.types import BrushType, TextureParams

if TYPE_CHECKING:
    pass


def create_block(
    min_pt: Vec3,
    max_pt: Vec3,
    shader: str = "common/caulk",
) -> Brush:
    """
    Create a simple box/block brush.

    This is a wrapper around create_brush_box for consistency.

    Args:
        min_pt: Minimum corner
        max_pt: Maximum corner
        shader: Texture/shader name

    Returns:
        A new box Brush
    """
    return create_brush_box(min_pt, max_pt, shader)


def create_cylinder(
    center: Vec3,
    radius: float,
    height: float,
    sides: int = 8,
    shader: str = "common/caulk",
) -> Brush:
    """
    Create a cylindrical brush.

    Args:
        center: Center point at the base of the cylinder
        radius: Radius of the cylinder
        height: Height of the cylinder (extends in +Z)
        sides: Number of sides (minimum 3)
        shader: Shader name for all faces

    Returns:
        A new Brush approximating a cylinder
    """
    sides = max(3, sides)
    texture = TextureParams()

    planes = []

    # Generate side faces
    for i in range(sides):
        angle1 = 2 * math.pi * i / sides
        angle2 = 2 * math.pi * ((i + 1) % sides) / sides

        # Points on the circle at base and top
        x1 = center.x + radius * math.cos(angle1)
        y1 = center.y + radius * math.sin(angle1)
        x2 = center.x + radius * math.cos(angle2)
        y2 = center.y + radius * math.sin(angle2)

        z_base = center.z
        z_top = center.z + height

        # Side face plane - winding for normal pointing inward
        plane = BrushPlane(
            point1=Vec3(x2, y2, z_top),
            point2=Vec3(x2, y2, z_base),
            point3=Vec3(x1, y1, z_base),
            shader=shader,
            texture=texture.copy(),
        )
        planes.append(plane)

    # Top face - use first 3 points of top circle
    top_points = []
    for i in range(3):
        angle = 2 * math.pi * i / sides
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        top_points.append(Vec3(x, y, center.z + height))

    top_plane = BrushPlane(
        point1=top_points[2],
        point2=top_points[1],
        point3=top_points[0],
        shader=shader,
        texture=texture.copy(),
    )
    planes.append(top_plane)

    # Bottom face
    bottom_points = []
    for i in range(3):
        angle = 2 * math.pi * i / sides
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        bottom_points.append(Vec3(x, y, center.z))

    bottom_plane = BrushPlane(
        point1=bottom_points[0],
        point2=bottom_points[1],
        point3=bottom_points[2],
        shader=shader,
        texture=texture.copy(),
    )
    planes.append(bottom_plane)

    return Brush(brush_type=BrushType.REGULAR, planes=planes)


def create_cone(
    center: Vec3,
    radius: float,
    height: float,
    sides: int = 8,
    shader: str = "common/caulk",
) -> Brush:
    """
    Create a conical brush.

    Args:
        center: Center point at the base of the cone
        radius: Radius of the base
        height: Height of the cone (apex at center.z + height)
        sides: Number of sides (minimum 3)
        shader: Shader name for all faces

    Returns:
        A new Brush approximating a cone
    """
    sides = max(3, sides)
    texture = TextureParams()

    planes = []
    apex = Vec3(center.x, center.y, center.z + height)

    # Generate side faces (triangular)
    for i in range(sides):
        angle1 = 2 * math.pi * i / sides
        angle2 = 2 * math.pi * ((i + 1) % sides) / sides

        x1 = center.x + radius * math.cos(angle1)
        y1 = center.y + radius * math.sin(angle1)
        x2 = center.x + radius * math.cos(angle2)
        y2 = center.y + radius * math.sin(angle2)

        z_base = center.z

        # Side face - 3 points: apex and two base corners
        plane = BrushPlane(
            point1=apex.copy(),
            point2=Vec3(x2, y2, z_base),
            point3=Vec3(x1, y1, z_base),
            shader=shader,
            texture=texture.copy(),
        )
        planes.append(plane)

    # Bottom face
    bottom_points = []
    for i in range(3):
        angle = 2 * math.pi * i / sides
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        bottom_points.append(Vec3(x, y, center.z))

    bottom_plane = BrushPlane(
        point1=bottom_points[0],
        point2=bottom_points[1],
        point3=bottom_points[2],
        shader=shader,
        texture=texture.copy(),
    )
    planes.append(bottom_plane)

    return Brush(brush_type=BrushType.REGULAR, planes=planes)


def create_wedge(
    min_pt: Vec3,
    max_pt: Vec3,
    shader: str = "common/caulk",
) -> Brush:
    """
    Create a wedge (triangular prism) brush.

    The wedge has a sloped face from the top-front edge to the bottom-back edge.

    Args:
        min_pt: Minimum corner
        max_pt: Maximum corner
        shader: Shader name for all faces

    Returns:
        A new Brush forming a wedge
    """
    texture = TextureParams()

    # Ensure min < max
    x0 = min(min_pt.x, max_pt.x)
    y0 = min(min_pt.y, max_pt.y)
    z0 = min(min_pt.z, max_pt.z)
    x1 = max(min_pt.x, max_pt.x)
    y1 = max(min_pt.y, max_pt.y)
    z1 = max(min_pt.z, max_pt.z)

    planes = [
        # Bottom face
        BrushPlane(
            point1=Vec3(x0, y0, z0),
            point2=Vec3(x1, y0, z0),
            point3=Vec3(x1, y1, z0),
            shader=shader,
            texture=texture.copy(),
        ),
        # Front face (Y-)
        BrushPlane(
            point1=Vec3(x0, y0, z1),
            point2=Vec3(x1, y0, z1),
            point3=Vec3(x1, y0, z0),
            shader=shader,
            texture=texture.copy(),
        ),
        # Left face (X-)
        BrushPlane(
            point1=Vec3(x0, y0, z0),
            point2=Vec3(x0, y1, z0),
            point3=Vec3(x0, y0, z1),
            shader=shader,
            texture=texture.copy(),
        ),
        # Right face (X+)
        BrushPlane(
            point1=Vec3(x1, y1, z0),
            point2=Vec3(x1, y0, z0),
            point3=Vec3(x1, y0, z1),
            shader=shader,
            texture=texture.copy(),
        ),
        # Slope face
        BrushPlane(
            point1=Vec3(x0, y0, z1),
            point2=Vec3(x0, y1, z0),
            point3=Vec3(x1, y1, z0),
            shader=shader,
            texture=texture.copy(),
        ),
    ]

    return Brush(brush_type=BrushType.REGULAR, planes=planes)


def create_spike(
    center: Vec3,
    base_size: float,
    height: float,
    shader: str = "common/caulk",
) -> Brush:
    """
    Create a 4-sided pyramid/spike brush.

    Args:
        center: Center point at the base
        base_size: Half-width of the square base
        height: Height of the spike
        shader: Shader name for all faces

    Returns:
        A new Brush forming a 4-sided pyramid
    """
    texture = TextureParams()
    apex = Vec3(center.x, center.y, center.z + height)

    # Base corners
    corners = [
        Vec3(center.x - base_size, center.y - base_size, center.z),
        Vec3(center.x + base_size, center.y - base_size, center.z),
        Vec3(center.x + base_size, center.y + base_size, center.z),
        Vec3(center.x - base_size, center.y + base_size, center.z),
    ]

    planes = [
        # Bottom face
        BrushPlane(
            point1=corners[0],
            point2=corners[1],
            point3=corners[2],
            shader=shader,
            texture=texture.copy(),
        ),
        # Side faces (4 triangular faces)
        BrushPlane(
            point1=corners[1],
            point2=corners[0],
            point3=apex.copy(),
            shader=shader,
            texture=texture.copy(),
        ),
        BrushPlane(
            point1=corners[2],
            point2=corners[1],
            point3=apex.copy(),
            shader=shader,
            texture=texture.copy(),
        ),
        BrushPlane(
            point1=corners[3],
            point2=corners[2],
            point3=apex.copy(),
            shader=shader,
            texture=texture.copy(),
        ),
        BrushPlane(
            point1=corners[0],
            point2=corners[3],
            point3=apex.copy(),
            shader=shader,
            texture=texture.copy(),
        ),
    ]

    return Brush(brush_type=BrushType.REGULAR, planes=planes)


# Alias for backward compatibility naming
create_pyramid = create_spike
