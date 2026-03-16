"""
CoD1 Map Parser - Patch Module
==============================

Patch surfaces (terrain meshes and bezier curves) for the CoD1 map format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .math import Vec3, Color
from .types import BrushType, PatchParams


@dataclass
class PatchVertex:
    """
    A single vertex in a patch (terrain or curve).

    CoD1 Format: ( x y z u v r g b alpha turned_edge )

    Attributes:
        position: 3D position (x, y, z)
        uv: Texture coordinates (u, v)
        color: Vertex color (RGBA)
        turned_edge: Edge direction flag (0 or 1) - controls which diagonal
                    is used when triangulating the quad to the right/below this vertex
    """
    position: Vec3 = field(default_factory=Vec3.zero)
    uv: Tuple[float, float] = (0.0, 0.0)
    color: Color = field(default_factory=Color.white)
    turned_edge: int = 0

    @property
    def x(self) -> float:
        return self.position.x

    @x.setter
    def x(self, value: float) -> None:
        self.position.x = value

    @property
    def y(self) -> float:
        return self.position.y

    @y.setter
    def y(self, value: float) -> None:
        self.position.y = value

    @property
    def z(self) -> float:
        return self.position.z

    @z.setter
    def z(self, value: float) -> None:
        self.position.z = value

    @property
    def u(self) -> float:
        return self.uv[0]

    @u.setter
    def u(self, value: float) -> None:
        self.uv = (value, self.uv[1])

    @property
    def v(self) -> float:
        return self.uv[1]

    @v.setter
    def v(self, value: float) -> None:
        self.uv = (self.uv[0], value)

    def to_map_string(self) -> str:
        """Convert to .map format string."""
        def fmt(val: float) -> str:
            if abs(val - round(val)) < 1e-6:
                return str(int(round(val)))
            return f"{val:g}"
        return (f"( {fmt(self.position.x)} {fmt(self.position.y)} {fmt(self.position.z)} "
                f"{fmt(self.uv[0])} {fmt(self.uv[1])} "
                f"{self.color.r} {self.color.g} {self.color.b} {self.color.a} {self.turned_edge} )")

    @classmethod
    def from_values(cls, x: float, y: float, z: float,
                    u: float = 0.0, v: float = 0.0,
                    r: int = 255, g: int = 255, b: int = 255, a: int = 255,
                    turned_edge: int = 0) -> 'PatchVertex':
        """Create vertex from individual values."""
        return cls(
            position=Vec3(x, y, z),
            uv=(u, v),
            color=Color(r, g, b, a),
            turned_edge=turned_edge
        )

    def copy(self) -> 'PatchVertex':
        """Create a deep copy."""
        return PatchVertex(
            position=self.position.copy(),
            uv=self.uv,
            color=self.color.copy(),
            turned_edge=self.turned_edge
        )

    def __repr__(self) -> str:
        return f"PatchVertex(pos={self.position}, uv={self.uv})"


@dataclass
class Patch:
    """
    A patch surface (terrain mesh or bezier curve).

    CoD1 Format:
        patchTerrainDef3 (or patchDef5)
        {
            shader_name
            ( rows cols contents 0 0 0 subdivision )
            (
            ( vertex vertex ... )
            ( vertex vertex ... )
            ...
            )
        }

    Attributes:
        patch_type: Type of patch (TERRAIN or CURVE)
        shader: Texture/material name
        params: Patch parameters
        vertices: 2D grid of vertices [row][col]
    """
    patch_type: BrushType = BrushType.TERRAIN
    shader: str = "common/caulk"
    params: PatchParams = field(default_factory=PatchParams)
    vertices: List[List[PatchVertex]] = field(default_factory=list)

    @property
    def rows(self) -> int:
        """Number of vertex rows."""
        return len(self.vertices)

    @property
    def cols(self) -> int:
        """Number of vertices per row."""
        if self.vertices:
            return len(self.vertices[0])
        return 0

    @property
    def vertex_count(self) -> int:
        """Total number of vertices."""
        return self.rows * self.cols

    @property
    def is_terrain(self) -> bool:
        """Check if this is a terrain patch (patchTerrainDef3)."""
        return self.patch_type == BrushType.TERRAIN

    @property
    def is_curve(self) -> bool:
        """Check if this is a curve patch (patchDef5)."""
        return self.patch_type == BrushType.CURVE

    @property
    def type_name(self) -> str:
        """Get the type name as used in .map file."""
        if self.patch_type == BrushType.TERRAIN:
            return "patchTerrainDef3"
        return "patchDef5"

    def get_vertex(self, row: int, col: int) -> Optional[PatchVertex]:
        """Get vertex at specified row and column."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.vertices[row][col]
        return None

    def set_vertex(self, row: int, col: int, vertex: PatchVertex) -> bool:
        """Set vertex at specified row and column."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            self.vertices[row][col] = vertex
            return True
        return False

    def get_vertex_position(self, row: int, col: int) -> Optional[Vec3]:
        """Get position of vertex at row, col."""
        vertex = self.get_vertex(row, col)
        return vertex.position if vertex else None

    def set_vertex_position(self, row: int, col: int, position: Vec3) -> bool:
        """Set position of vertex at row, col."""
        vertex = self.get_vertex(row, col)
        if vertex:
            vertex.position = position
            return True
        return False

    def get_vertex_height(self, row: int, col: int) -> Optional[float]:
        """Get Z coordinate of vertex at row, col."""
        vertex = self.get_vertex(row, col)
        return vertex.position.z if vertex else None

    def set_vertex_height(self, row: int, col: int, height: float) -> bool:
        """Set Z coordinate of vertex at row, col."""
        vertex = self.get_vertex(row, col)
        if vertex:
            vertex.position.z = height
            return True
        return False

    def get_all_vertices(self) -> List[PatchVertex]:
        """Get all vertices as a flat list."""
        return [v for row in self.vertices for v in row]

    def get_bounding_box(self) -> Tuple[Vec3, Vec3]:
        """Calculate bounding box of all vertices."""
        all_verts = self.get_all_vertices()
        if not all_verts:
            return Vec3.zero(), Vec3.zero()

        min_pos = Vec3(
            min(v.position.x for v in all_verts),
            min(v.position.y for v in all_verts),
            min(v.position.z for v in all_verts)
        )
        max_pos = Vec3(
            max(v.position.x for v in all_verts),
            max(v.position.y for v in all_verts),
            max(v.position.z for v in all_verts)
        )
        return min_pos, max_pos

    def get_center(self) -> Vec3:
        """Get center point of the patch."""
        min_pos, max_pos = self.get_bounding_box()
        return (min_pos + max_pos) * 0.5

    def translate(self, offset: Vec3) -> None:
        """Move all vertices by offset."""
        for row in self.vertices:
            for vertex in row:
                vertex.position = vertex.position + offset

    def scale(self, factor: float, center: Optional[Vec3] = None) -> None:
        """Scale the patch around a center point."""
        if center is None:
            center = self.get_center()
        for row in self.vertices:
            for vertex in row:
                offset = vertex.position - center
                vertex.position = center + offset * factor

    def rotate(self, angle: float, axis: int, center: Optional[Vec3] = None) -> None:
        """
        Rotate the patch around an axis.

        Args:
            angle: Rotation angle in radians
            axis: Axis index (0=X, 1=Y, 2=Z)
            center: Center point of rotation (defaults to patch center)
        """
        import math

        if center is None:
            center = self.get_center()

        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        for row in self.vertices:
            for vertex in row:
                p = vertex.position
                px = p.x - center.x
                py = p.y - center.y
                pz = p.z - center.z

                if axis == 0:  # X-axis
                    new_y = py * cos_a - pz * sin_a
                    new_z = py * sin_a + pz * cos_a
                    vertex.position = Vec3(px + center.x, new_y + center.y, new_z + center.z)
                elif axis == 1:  # Y-axis
                    new_x = px * cos_a + pz * sin_a
                    new_z = -px * sin_a + pz * cos_a
                    vertex.position = Vec3(new_x + center.x, py + center.y, new_z + center.z)
                else:  # Z-axis
                    new_x = px * cos_a - py * sin_a
                    new_y = px * sin_a + py * cos_a
                    vertex.position = Vec3(new_x + center.x, new_y + center.y, pz + center.z)

    def flip(self, axis: int, center: Optional[Vec3] = None) -> None:
        """
        Mirror the patch across a plane through center.

        Args:
            axis: Axis to flip (0=X, 1=Y, 2=Z)
            center: Center point of the flip plane (defaults to patch center)
        """
        if center is None:
            center = self.get_center()

        for row in self.vertices:
            for vertex in row:
                p = vertex.position
                if axis == 0:
                    vertex.position = Vec3(2 * center.x - p.x, p.y, p.z)
                elif axis == 1:
                    vertex.position = Vec3(p.x, 2 * center.y - p.y, p.z)
                else:
                    vertex.position = Vec3(p.x, p.y, 2 * center.z - p.z)

    def to_map_string(self, indent: str = "  ") -> str:
        """Convert to .map format string."""
        lines = [self.type_name, "{"]
        lines.append(f"{indent}{self.shader}")
        lines.append(f"{indent}{self.params.to_map_string()}")
        lines.append("(")
        for row in self.vertices:
            row_str = "( " + " ".join(v.to_map_string() for v in row) + " )"
            lines.append(row_str)
        lines.append(")")
        lines.append("}")
        return "\n".join(lines)

    def copy(self) -> 'Patch':
        """Create a deep copy."""
        new_patch = Patch(
            patch_type=self.patch_type,
            shader=self.shader,
            params=self.params.copy()
        )
        new_patch.vertices = [[v.copy() for v in row] for row in self.vertices]
        return new_patch

    def __repr__(self) -> str:
        return f"Patch({self.type_name}, shader='{self.shader}', size={self.rows}x{self.cols})"
