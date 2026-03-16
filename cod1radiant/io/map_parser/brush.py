"""
CoD1 Map Parser - Brush Module
==============================

Brush geometry (planes and complete brushes) for the CoD1 map format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple, Iterator

from .math import Vec3
from .types import BrushType, TextureParams, TOOL_SHADERS
from .patch import Patch


@dataclass
class BrushPlane:
    """
    A single brush plane defined by three points.

    CoD1 Format:
        ( x1 y1 z1 ) ( x2 y2 z2 ) ( x3 y3 z3 ) shader offset_x offset_y rotation scale_x scale_y content_flags surface_flags value 0

    The three points define a plane in 3D space. The plane normal points
    towards the inside of the brush (using right-hand rule with counter-clockwise
    winding when viewed from outside the brush).

    Attributes:
        point1, point2, point3: Three points defining the plane
        shader: Texture/material name
        texture: Texture mapping parameters
    """
    point1: Vec3 = field(default_factory=Vec3.zero)
    point2: Vec3 = field(default_factory=Vec3.zero)
    point3: Vec3 = field(default_factory=Vec3.zero)
    shader: str = "common/caulk"
    texture: TextureParams = field(default_factory=TextureParams)

    @property
    def normal(self) -> Vec3:
        """Calculate plane normal from the three points."""
        v1 = self.point2 - self.point1
        v2 = self.point3 - self.point1
        return v1.cross(v2).normalize()

    @property
    def distance(self) -> float:
        """Calculate plane distance from origin."""
        return self.normal.dot(self.point1)

    @property
    def content_flags(self) -> int:
        """Get content flags from texture params."""
        return self.texture.content_flags

    @content_flags.setter
    def content_flags(self, value: int) -> None:
        """Set content flags."""
        self.texture.content_flags = value

    @property
    def surface_flags(self) -> int:
        """Get surface flags from texture params."""
        return self.texture.surface_flags

    @surface_flags.setter
    def surface_flags(self, value: int) -> None:
        """Set surface flags."""
        self.texture.surface_flags = value

    def get_points(self) -> Tuple[Vec3, Vec3, Vec3]:
        """Get all three points as tuple."""
        return (self.point1, self.point2, self.point3)

    def set_points(self, p1: Vec3, p2: Vec3, p3: Vec3) -> None:
        """Set all three points."""
        self.point1 = p1
        self.point2 = p2
        self.point3 = p3

    def translate(self, offset: Vec3) -> None:
        """Move the plane by offset."""
        self.point1 = self.point1 + offset
        self.point2 = self.point2 + offset
        self.point3 = self.point3 + offset

    def is_tool_shader(self) -> bool:
        """Check if shader is a tool shader (common/*)."""
        return self.shader in TOOL_SHADERS or self.shader.startswith("common/")

    def to_map_string(self) -> str:
        """Convert to .map file format string."""
        return (f"( {self.point1.to_string()} ) "
                f"( {self.point2.to_string()} ) "
                f"( {self.point3.to_string()} ) "
                f"{self.shader} {self.texture.to_string()}")

    def copy(self) -> 'BrushPlane':
        """Create a deep copy."""
        return BrushPlane(
            point1=self.point1.copy(),
            point2=self.point2.copy(),
            point3=self.point3.copy(),
            shader=self.shader,
            texture=self.texture.copy()
        )

    def __repr__(self) -> str:
        return f"BrushPlane(shader='{self.shader}', normal={self.normal})"


@dataclass
class Brush:
    """
    A brush element which can be either a regular brush or a patch.

    Regular brushes are convex volumes defined by at least 4 planes.
    Patches are curved surfaces (terrain or bezier curves).

    Attributes:
        index: Brush index within entity
        brush_type: Type of brush (REGULAR, TERRAIN, or CURVE)
        planes: List of planes (for regular brushes)
        patch: Patch data (for terrain/curve brushes)
    """
    index: int = 0
    brush_type: BrushType = BrushType.REGULAR
    planes: List[BrushPlane] = field(default_factory=list)
    patch: Optional[Patch] = None

    @property
    def is_regular(self) -> bool:
        """Check if this is a regular plane-based brush."""
        return self.brush_type == BrushType.REGULAR

    @property
    def is_terrain(self) -> bool:
        """Check if this is a terrain patch (patchTerrainDef3)."""
        return self.brush_type == BrushType.TERRAIN

    @property
    def is_curve(self) -> bool:
        """Check if this is a curve patch (patchDef5)."""
        return self.brush_type == BrushType.CURVE

    @property
    def is_patch(self) -> bool:
        """Check if this is any type of patch."""
        return self.brush_type in (BrushType.TERRAIN, BrushType.CURVE)

    @property
    def plane_count(self) -> int:
        """Number of planes (for regular brushes)."""
        return len(self.planes)

    @property
    def is_valid(self) -> bool:
        """Check if brush is valid."""
        if self.is_regular:
            return len(self.planes) >= 4
        return self.patch is not None

    def get_plane(self, index: int) -> Optional[BrushPlane]:
        """Get plane at index."""
        if 0 <= index < len(self.planes):
            return self.planes[index]
        return None

    def add_plane(self, plane: BrushPlane) -> None:
        """Add a plane to the brush."""
        self.planes.append(plane)

    def remove_plane(self, index: int) -> Optional[BrushPlane]:
        """Remove and return plane at index."""
        if 0 <= index < len(self.planes):
            return self.planes.pop(index)
        return None

    def get_shaders(self) -> List[str]:
        """Get list of all unique shaders used."""
        if self.is_regular:
            return list(set(p.shader for p in self.planes))
        elif self.patch:
            return [self.patch.shader]
        return []

    def get_primary_shader(self) -> str:
        """Get most common shader (for regular brush) or patch shader."""
        if self.is_patch and self.patch:
            return self.patch.shader
        if not self.planes:
            return "common/caulk"
        shader_counts: Dict[str, int] = {}
        for plane in self.planes:
            shader_counts[plane.shader] = shader_counts.get(plane.shader, 0) + 1
        return max(shader_counts, key=shader_counts.get)  # type: ignore

    def set_all_shaders(self, shader: str) -> None:
        """Set shader on all planes."""
        for plane in self.planes:
            plane.shader = shader

    def get_content_flags(self) -> int:
        """Get content flags (from first plane or patch)."""
        if self.is_patch and self.patch:
            return self.patch.params.contents
        if self.planes:
            return self.planes[0].content_flags
        return 0

    def set_content_flags(self, flags: int) -> None:
        """Set content flags on all elements."""
        if self.is_patch and self.patch:
            self.patch.params.contents = flags
        for plane in self.planes:
            plane.content_flags = flags

    def get_bounding_box(self) -> Tuple[Vec3, Vec3]:
        """Calculate bounding box."""
        if self.is_patch and self.patch:
            return self.patch.get_bounding_box()

        if not self.planes:
            return Vec3.zero(), Vec3.zero()

        all_points: List[Vec3] = []
        for plane in self.planes:
            all_points.extend([plane.point1, plane.point2, plane.point3])

        min_pos = Vec3(
            min(p.x for p in all_points),
            min(p.y for p in all_points),
            min(p.z for p in all_points)
        )
        max_pos = Vec3(
            max(p.x for p in all_points),
            max(p.y for p in all_points),
            max(p.z for p in all_points)
        )
        return min_pos, max_pos

    def get_center(self) -> Vec3:
        """Get center point of the brush."""
        min_pos, max_pos = self.get_bounding_box()
        return (min_pos + max_pos) * 0.5

    def translate(self, offset: Vec3) -> None:
        """Move the brush by offset."""
        if self.is_patch and self.patch:
            self.patch.translate(offset)
        for plane in self.planes:
            plane.translate(offset)

    def rotate(self, angle: float, axis: int, center: Vec3) -> None:
        """
        Rotate the brush around an axis.

        Args:
            angle: Rotation angle in radians
            axis: Axis index (0=X, 1=Y, 2=Z)
            center: Center point of rotation
        """
        import math

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        def rotate_point(p: Vec3) -> Vec3:
            # Translate to origin
            px = p.x - center.x
            py = p.y - center.y
            pz = p.z - center.z

            # Rotate based on axis
            if axis == 0:  # X-axis
                new_y = py * cos_a - pz * sin_a
                new_z = py * sin_a + pz * cos_a
                return Vec3(px + center.x, new_y + center.y, new_z + center.z)
            elif axis == 1:  # Y-axis
                new_x = px * cos_a + pz * sin_a
                new_z = -px * sin_a + pz * cos_a
                return Vec3(new_x + center.x, py + center.y, new_z + center.z)
            else:  # Z-axis
                new_x = px * cos_a - py * sin_a
                new_y = px * sin_a + py * cos_a
                return Vec3(new_x + center.x, new_y + center.y, pz + center.z)

        for plane in self.planes:
            plane.point1 = rotate_point(plane.point1)
            plane.point2 = rotate_point(plane.point2)
            plane.point3 = rotate_point(plane.point3)

        if self.is_patch and self.patch:
            self.patch.rotate(angle, axis, center)

    def scale(self, factor: float, center: Vec3) -> None:
        """
        Scale the brush from a center point.

        Args:
            factor: Scale factor (1.0 = no change)
            center: Center point to scale from
        """
        def scale_point(p: Vec3) -> Vec3:
            return Vec3(
                center.x + (p.x - center.x) * factor,
                center.y + (p.y - center.y) * factor,
                center.z + (p.z - center.z) * factor
            )

        for plane in self.planes:
            plane.point1 = scale_point(plane.point1)
            plane.point2 = scale_point(plane.point2)
            plane.point3 = scale_point(plane.point3)

        if self.is_patch and self.patch:
            self.patch.scale(factor, center)

    def flip(self, axis: int, center: Vec3) -> None:
        """
        Mirror the brush across a plane through center.

        Args:
            axis: Axis to flip (0=X, 1=Y, 2=Z)
            center: Center point of the flip plane
        """
        def flip_point(p: Vec3) -> Vec3:
            if axis == 0:
                return Vec3(2 * center.x - p.x, p.y, p.z)
            elif axis == 1:
                return Vec3(p.x, 2 * center.y - p.y, p.z)
            else:
                return Vec3(p.x, p.y, 2 * center.z - p.z)

        for plane in self.planes:
            # Flip points
            plane.point1 = flip_point(plane.point1)
            plane.point2 = flip_point(plane.point2)
            plane.point3 = flip_point(plane.point3)
            # Swap winding to maintain correct normal direction
            plane.point1, plane.point3 = plane.point3, plane.point1

        if self.is_patch and self.patch:
            self.patch.flip(axis, center)

    def to_map_string(self) -> str:
        """Convert to .map format string."""
        lines = [f"// brush {self.index}", "{"]

        if self.is_patch and self.patch:
            lines.append(self.patch.to_map_string())
        else:
            for plane in self.planes:
                lines.append(f"  {plane.to_map_string()}")

        lines.append("}")
        return "\n".join(lines)

    def copy(self) -> 'Brush':
        """Create a deep copy."""
        new_brush = Brush(
            index=self.index,
            brush_type=self.brush_type,
            patch=self.patch.copy() if self.patch else None
        )
        new_brush.planes = [p.copy() for p in self.planes]
        return new_brush

    def __iter__(self) -> Iterator[BrushPlane]:
        """Iterate over planes."""
        return iter(self.planes)

    def __len__(self) -> int:
        """Number of planes."""
        return len(self.planes)

    def __bool__(self) -> bool:
        """Brush is truthy if valid (has 4+ planes or has patch)."""
        return self.is_valid

    def __getitem__(self, index: int) -> BrushPlane:
        """Get plane by index."""
        return self.planes[index]

    def __repr__(self) -> str:
        if self.is_patch:
            return f"Brush({self.index}, {self.brush_type.name}, shader={self.get_primary_shader()})"
        return f"Brush({self.index}, {self.plane_count} planes, shader={self.get_primary_shader()})"
