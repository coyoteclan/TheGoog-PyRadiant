"""
CoD1 Map Parser - Entity Module
===============================

Entity classes for the CoD1 map format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Iterator

from .math import Vec3
from .brush import Brush


@dataclass
class Entity:
    """
    A map entity with properties and optional brushes.

    Entity 0 is always "worldspawn" containing world geometry.
    Other entities can be point entities (origin only) or brush entities.

    Attributes:
        index: Entity index in map
        properties: Key-value properties
        brushes: List of brushes
    """
    index: int = 0
    properties: Dict[str, str] = field(default_factory=dict)
    brushes: List[Brush] = field(default_factory=list)

    @property
    def classname(self) -> str:
        """Get entity classname."""
        return self.properties.get("classname", "")

    @classname.setter
    def classname(self, value: str) -> None:
        """Set entity classname."""
        self.properties["classname"] = value

    @property
    def is_worldspawn(self) -> bool:
        """Check if this is the worldspawn entity."""
        return self.classname == "worldspawn"

    @property
    def has_brushes(self) -> bool:
        """Check if entity has brushes."""
        return len(self.brushes) > 0

    @property
    def is_point_entity(self) -> bool:
        """Check if this is a point entity (no brushes)."""
        return not self.has_brushes and "origin" in self.properties

    @property
    def is_brush_entity(self) -> bool:
        """Check if this is a brush entity."""
        return self.has_brushes and not self.is_worldspawn

    @property
    def brush_count(self) -> int:
        """Number of brushes."""
        return len(self.brushes)

    # Property accessors
    def get_property(self, key: str, default: str = "") -> str:
        """Get property value."""
        return self.properties.get(key, default)

    def set_property(self, key: str, value: str) -> None:
        """Set property value."""
        self.properties[key] = value

    def has_property(self, key: str) -> bool:
        """Check if property exists."""
        return key in self.properties

    def remove_property(self, key: str) -> Optional[str]:
        """Remove and return property value."""
        return self.properties.pop(key, None)

    # Common properties
    @property
    def origin(self) -> Optional[Vec3]:
        """Get entity origin."""
        if "origin" in self.properties:
            return Vec3.from_string(self.properties["origin"])
        return None

    @origin.setter
    def origin(self, value: Vec3) -> None:
        """Set entity origin."""
        self.properties["origin"] = value.to_string()

    @property
    def angles(self) -> Optional[Vec3]:
        """Get entity angles (pitch yaw roll)."""
        if "angles" in self.properties:
            return Vec3.from_string(self.properties["angles"])
        if "angle" in self.properties:
            # Single angle is yaw only
            return Vec3(0, float(self.properties["angle"]), 0)
        return None

    @angles.setter
    def angles(self, value: Vec3) -> None:
        """Set entity angles."""
        self.properties["angles"] = value.to_string()

    @property
    def targetname(self) -> Optional[str]:
        """Get entity targetname."""
        return self.properties.get("targetname")

    @targetname.setter
    def targetname(self, value: str) -> None:
        """Set entity targetname."""
        self.properties["targetname"] = value

    @property
    def target(self) -> Optional[str]:
        """Get entity target."""
        return self.properties.get("target")

    @target.setter
    def target(self, value: str) -> None:
        """Set entity target."""
        self.properties["target"] = value

    @property
    def model(self) -> Optional[str]:
        """Get entity model."""
        return self.properties.get("model")

    @model.setter
    def model(self, value: str) -> None:
        """Set entity model."""
        self.properties["model"] = value

    # Brush operations
    def get_brush(self, index: int) -> Optional[Brush]:
        """Get brush at index."""
        if 0 <= index < len(self.brushes):
            return self.brushes[index]
        return None

    def add_brush(self, brush: Brush) -> None:
        """Add a brush."""
        brush.index = len(self.brushes)
        self.brushes.append(brush)

    def remove_brush(self, index: int) -> Optional[Brush]:
        """Remove and return brush at index."""
        if 0 <= index < len(self.brushes):
            brush = self.brushes.pop(index)
            # Reindex remaining brushes
            for i, b in enumerate(self.brushes):
                b.index = i
            return brush
        return None

    def get_regular_brushes(self) -> List[Brush]:
        """Get all regular (plane-based) brushes."""
        return [b for b in self.brushes if b.is_regular]

    def get_terrain_patches(self) -> List[Brush]:
        """Get all terrain patches (patchTerrainDef3)."""
        return [b for b in self.brushes if b.is_terrain]

    def get_curve_patches(self) -> List[Brush]:
        """Get all curve patches (patchDef5)."""
        return [b for b in self.brushes if b.is_curve]

    def get_all_patches(self) -> List[Brush]:
        """Get all patches (terrain and curve)."""
        return [b for b in self.brushes if b.is_patch]

    def get_brushes_by_shader(self, shader: str) -> List[Brush]:
        """Get all brushes using specified shader."""
        return [b for b in self.brushes if shader in b.get_shaders()]

    def get_all_shaders(self) -> List[str]:
        """Get list of all unique shaders used."""
        shaders: set = set()
        for brush in self.brushes:
            shaders.update(brush.get_shaders())
        return sorted(shaders)

    def to_map_string(self) -> str:
        """Convert to .map format string."""
        lines = [f"// entity {self.index}", "{"]

        # Ensure classname is first
        if "classname" in self.properties:
            lines.append(f'"classname" "{self.properties["classname"]}"')

        for key, value in self.properties.items():
            if key != "classname":
                lines.append(f'"{key}" "{value}"')

        for brush in self.brushes:
            lines.append(brush.to_map_string())

        lines.append("}")
        return "\n".join(lines)

    def copy(self) -> 'Entity':
        """Create a deep copy."""
        new_entity = Entity(
            index=self.index,
            properties=dict(self.properties)
        )
        new_entity.brushes = [b.copy() for b in self.brushes]
        return new_entity

    def __iter__(self) -> Iterator[Brush]:
        """Iterate over brushes."""
        return iter(self.brushes)

    def __len__(self) -> int:
        """Number of brushes."""
        return len(self.brushes)

    def __bool__(self) -> bool:
        """Entity is always truthy (even with no brushes)."""
        return True

    def __repr__(self) -> str:
        return f"Entity({self.index}, classname='{self.classname}', {self.brush_count} brushes)"
