"""
CoD1 Map Parser - Types Module
==============================

Enumerations and basic data types for the CoD1 map format.
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
from typing import List


class BrushType(Enum):
    """Type of brush content."""
    REGULAR = auto()      # Standard brush with plane definitions
    TERRAIN = auto()      # patchTerrainDef3 (terrain mesh)
    CURVE = auto()        # patchDef5 (bezier curve/surface)


class ContentFlag(Enum):
    """
    Common content flags used in CoD1.

    These flags control collision and BSP behavior.
    """
    STRUCTURAL = 0              # Standard structural (causes BSP splitting)
    DETAIL = 134217728          # Detail brush (no BSP split)
    NON_COLLIDING = 134217732   # No collision (DETAIL + 4)
    WEAPON_CLIP = 134226048     # Weapon clip (DETAIL + 8320)
    WEAPON_CLIP_DETAIL = 134226052  # NON_COLLIDING + WEAPON_CLIP combined


# Tool shaders that have special engine behavior
TOOL_SHADERS = {
    "common/caulk",         # Invisible surface (for hidden faces)
    "common/clip",          # Player collision only
    "common/clip_metal",    # Metal collision (metal sounds)
    "common/nodraw",        # Not rendered
    "common/trigger",       # Trigger volume
    "common/origin",        # Origin brush for rotating entities
    "common/hint",          # BSP hint brush
    "common/portal",        # Area portal
    "common/ladder",        # Ladder surface
    "common/water",         # Water volume
}


@dataclass
class TextureParams:
    """
    Texture mapping parameters for a brush plane.

    CoD1 Format: offset_x offset_y rotation scale_x scale_y content_flags surface_flags value [0]

    Attributes:
        offset_x: Texture offset along U axis
        offset_y: Texture offset along V axis
        rotation: Texture rotation in degrees
        scale_x: Texture scale along U axis (default 0.25 = 4 tiles per 256 units)
        scale_y: Texture scale along V axis
        content_flags: Content flags (collision, detail, etc.)
        surface_flags: Surface flags
        value: Additional value (usually 0)
    """
    offset_x: float = 0.0
    offset_y: float = 0.0
    rotation: float = 0.0
    scale_x: float = 0.25
    scale_y: float = 0.25
    content_flags: int = 0
    surface_flags: int = 0
    value: int = 0

    def to_string(self) -> str:
        """Convert to .map format string."""
        def fmt(v: float) -> str:
            if abs(v - round(v)) < 1e-6:
                return str(int(round(v)))
            return f"{v:g}"
        return (f"{fmt(self.offset_x)} {fmt(self.offset_y)} {fmt(self.rotation)} "
                f"{fmt(self.scale_x)} {fmt(self.scale_y)} "
                f"{self.content_flags} {self.surface_flags} {self.value} 0")

    @classmethod
    def from_parts(cls, parts: List[str]) -> 'TextureParams':
        """Parse from string parts."""
        return cls(
            offset_x=float(parts[0]) if len(parts) > 0 else 0.0,
            offset_y=float(parts[1]) if len(parts) > 1 else 0.0,
            rotation=float(parts[2]) if len(parts) > 2 else 0.0,
            scale_x=float(parts[3]) if len(parts) > 3 else 0.25,
            scale_y=float(parts[4]) if len(parts) > 4 else 0.25,
            content_flags=int(parts[5]) if len(parts) > 5 else 0,
            surface_flags=int(parts[6]) if len(parts) > 6 else 0,
            value=int(parts[7]) if len(parts) > 7 else 0
        )

    @classmethod
    def default(cls) -> 'TextureParams':
        """Return default texture parameters."""
        return cls()

    def copy(self) -> 'TextureParams':
        return TextureParams(
            self.offset_x, self.offset_y, self.rotation,
            self.scale_x, self.scale_y,
            self.content_flags, self.surface_flags, self.value
        )

    def __repr__(self) -> str:
        return (f"TextureParams(offset=({self.offset_x}, {self.offset_y}), "
                f"rot={self.rotation}, scale=({self.scale_x}, {self.scale_y}), "
                f"flags={self.content_flags})")


@dataclass
class PatchParams:
    """
    Parameters for a patch definition.

    CoD1 Format: ( rows cols contents 0 0 0 subdivision )

    Attributes:
        rows: Number of vertex rows
        cols: Number of vertex columns
        contents: Content flags
        subdivision: Tessellation level (default 8)
    """
    rows: int = 3
    cols: int = 3
    contents: int = 0
    reserved1: int = 0
    reserved2: int = 0
    reserved3: int = 0
    subdivision: int = 8

    def to_map_string(self) -> str:
        """Convert to .map format string."""
        return (f"( {self.rows} {self.cols} {self.contents} "
                f"{self.reserved1} {self.reserved2} {self.reserved3} {self.subdivision} )")

    @classmethod
    def from_string(cls, s: str) -> 'PatchParams':
        """Parse from string."""
        content = s.strip()
        if content.startswith('('):
            content = content[1:]
        if content.endswith(')'):
            content = content[:-1]

        parts = content.strip().split()
        return cls(
            rows=int(parts[0]) if len(parts) > 0 else 3,
            cols=int(parts[1]) if len(parts) > 1 else 3,
            contents=int(parts[2]) if len(parts) > 2 else 0,
            reserved1=int(parts[3]) if len(parts) > 3 else 0,
            reserved2=int(parts[4]) if len(parts) > 4 else 0,
            reserved3=int(parts[5]) if len(parts) > 5 else 0,
            subdivision=int(parts[6]) if len(parts) > 6 else 8
        )

    def copy(self) -> 'PatchParams':
        return PatchParams(
            self.rows, self.cols, self.contents,
            self.reserved1, self.reserved2, self.reserved3, self.subdivision
        )

    def __repr__(self) -> str:
        return f"PatchParams({self.rows}x{self.cols}, contents={self.contents}, subdiv={self.subdivision})"
