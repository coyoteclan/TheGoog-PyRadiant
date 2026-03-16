"""
CoD1 Map Parser - Map Module
============================

Top-level map container for the CoD1 map format.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Iterator, Any

from .math import Vec3
from .types import BrushType, PatchParams
from .brush import Brush, BrushPlane
from .patch import Patch, PatchVertex
from .entity import Entity


@dataclass
class CoD1Map:
    """
    Complete CoD1 .map file representation.

    Contains all entities, brushes, and patches with full accessability.

    Attributes:
        entities: List of all entities
        filepath: Source file path (if loaded from file)
    """
    entities: List[Entity] = field(default_factory=list)
    filepath: str = ""

    @property
    def worldspawn(self) -> Optional[Entity]:
        """Get the worldspawn entity (entity 0)."""
        for entity in self.entities:
            if entity.is_worldspawn:
                return entity
        return None

    @property
    def entity_count(self) -> int:
        """Number of entities."""
        return len(self.entities)

    @property
    def total_brush_count(self) -> int:
        """Total number of brushes across all entities."""
        return sum(e.brush_count for e in self.entities)

    @property
    def world_brush_count(self) -> int:
        """Number of brushes in worldspawn."""
        ws = self.worldspawn
        return ws.brush_count if ws else 0

    # Entity operations
    def get_entity(self, index: int) -> Optional[Entity]:
        """Get entity at index."""
        if 0 <= index < len(self.entities):
            return self.entities[index]
        return None

    def add_entity(self, entity: Entity) -> None:
        """Add an entity."""
        entity.index = len(self.entities)
        self.entities.append(entity)

    def remove_entity(self, index: int) -> Optional[Entity]:
        """Remove and return entity at index (cannot remove worldspawn)."""
        if index == 0:
            return None  # Cannot remove worldspawn
        if 0 < index < len(self.entities):
            entity = self.entities.pop(index)
            # Reindex remaining entities
            for i, e in enumerate(self.entities):
                e.index = i
            return entity
        return None

    def get_entities_by_classname(self, classname: str) -> List[Entity]:
        """Get all entities with specified classname."""
        return [e for e in self.entities if e.classname == classname]

    def get_point_entities(self) -> List[Entity]:
        """Get all point entities."""
        return [e for e in self.entities if e.is_point_entity]

    def get_brush_entities(self) -> List[Entity]:
        """Get all brush entities (excluding worldspawn)."""
        return [e for e in self.entities if e.is_brush_entity]

    def get_non_worldspawn_entities(self) -> List[Entity]:
        """Get all entities except worldspawn."""
        return [e for e in self.entities if not e.is_worldspawn]

    # Brush operations across all entities
    def get_all_brushes(self) -> List[Brush]:
        """Get all brushes from all entities."""
        brushes = []
        for entity in self.entities:
            brushes.extend(entity.brushes)
        return brushes

    def get_world_brushes(self) -> List[Brush]:
        """Get brushes from worldspawn only."""
        ws = self.worldspawn
        return ws.brushes if ws else []

    def get_all_regular_brushes(self) -> List[Brush]:
        """Get all regular brushes from all entities."""
        return [b for b in self.get_all_brushes() if b.is_regular]

    def get_all_terrain_patches(self) -> List[Brush]:
        """Get all terrain patches from all entities."""
        return [b for b in self.get_all_brushes() if b.is_terrain]

    def get_all_curve_patches(self) -> List[Brush]:
        """Get all curve patches from all entities."""
        return [b for b in self.get_all_brushes() if b.is_curve]

    def get_all_patches(self) -> List[Brush]:
        """Get all patches (terrain and curve) from all entities."""
        return [b for b in self.get_all_brushes() if b.is_patch]

    # Shader operations
    def get_all_shaders(self) -> List[str]:
        """Get list of all unique shaders used in map."""
        shaders: set = set()
        for entity in self.entities:
            shaders.update(entity.get_all_shaders())
        return sorted(shaders)

    def get_all_classnames(self) -> List[str]:
        """Get list of all unique classnames."""
        return sorted(set(e.classname for e in self.entities if e.classname))

    # Statistics
    def get_statistics(self) -> Dict[str, Any]:
        """Get map statistics."""
        regular_brushes = self.get_all_regular_brushes()
        terrain_patches = self.get_all_terrain_patches()
        curve_patches = self.get_all_curve_patches()

        return {
            "entity_count": self.entity_count,
            "total_brush_count": self.total_brush_count,
            "world_brush_count": self.world_brush_count,
            "regular_brush_count": len(regular_brushes),
            "terrain_patch_count": len(terrain_patches),
            "curve_patch_count": len(curve_patches),
            "point_entity_count": len(self.get_point_entities()),
            "brush_entity_count": len(self.get_brush_entities()),
            "unique_shaders": len(self.get_all_shaders()),
            "unique_classnames": len(self.get_all_classnames())
        }

    # File operations
    def to_map_string(self) -> str:
        """Convert to .map format string."""
        return "\n".join(e.to_map_string() for e in self.entities)

    def save(self, filepath: str) -> None:
        """Save to .map file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_map_string())
        self.filepath = filepath

    def copy(self) -> 'CoD1Map':
        """Create a deep copy."""
        new_map = CoD1Map(filepath=self.filepath)
        new_map.entities = [e.copy() for e in self.entities]
        return new_map

    def __iter__(self) -> Iterator[Entity]:
        """Iterate over entities."""
        return iter(self.entities)

    def __len__(self) -> int:
        """Number of entities."""
        return len(self.entities)

    def __getitem__(self, index: int) -> Entity:
        """Get entity by index."""
        return self.entities[index]

    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (f"CoD1Map({stats['entity_count']} entities, "
                f"{stats['total_brush_count']} brushes, "
                f"{stats['terrain_patch_count']} terrains, "
                f"{stats['curve_patch_count']} curves)")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_brush_box(mins: Vec3, maxs: Vec3, shader: str = "common/caulk") -> Brush:
    """
    Create an axis-aligned box brush.

    Args:
        mins: Minimum corner coordinates
        maxs: Maximum corner coordinates
        shader: Texture/material name

    Returns:
        Brush object
    """
    from .types import TextureParams

    brush = Brush(brush_type=BrushType.REGULAR)

    # CoD1 MAP format: plane normals point INWARD (toward brush interior)
    # Points are ordered counter-clockwise when viewed from inside the brush
    # This produces inward-pointing normals via cross product (p2-p1) × (p3-p1)

    # Bottom face (Z-) - normal points up (+Z), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(mins.x, maxs.y, mins.z),
        point2=Vec3(maxs.x, mins.y, mins.z),
        point3=Vec3(maxs.x, maxs.y, mins.z),
        shader=shader
    ))

    # Top face (Z+) - normal points down (-Z), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(mins.x, mins.y, maxs.z),
        point2=Vec3(maxs.x, maxs.y, maxs.z),
        point3=Vec3(maxs.x, mins.y, maxs.z),
        shader=shader
    ))

    # Front face (Y-) - normal points back (+Y), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(mins.x, mins.y, mins.z),
        point2=Vec3(maxs.x, mins.y, maxs.z),
        point3=Vec3(maxs.x, mins.y, mins.z),
        shader=shader
    ))

    # Back face (Y+) - normal points forward (-Y), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(maxs.x, maxs.y, mins.z),
        point2=Vec3(mins.x, maxs.y, maxs.z),
        point3=Vec3(mins.x, maxs.y, mins.z),
        shader=shader
    ))

    # Left face (X-) - normal points right (+X), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(mins.x, maxs.y, mins.z),
        point2=Vec3(mins.x, mins.y, maxs.z),
        point3=Vec3(mins.x, mins.y, mins.z),
        shader=shader
    ))

    # Right face (X+) - normal points left (-X), into the brush
    brush.add_plane(BrushPlane(
        point1=Vec3(maxs.x, mins.y, mins.z),
        point2=Vec3(maxs.x, maxs.y, maxs.z),
        point3=Vec3(maxs.x, maxs.y, mins.z),
        shader=shader
    ))

    return brush


def create_terrain_patch(shader: str, rows: int, cols: int,
                         origin: Vec3 = None,
                         spacing: float = 64.0) -> Patch:
    """
    Create a flat terrain patch.

    Args:
        shader: Texture/material name
        rows: Number of vertex rows
        cols: Number of vertex columns
        origin: Bottom-left corner position
        spacing: Distance between vertices

    Returns:
        Patch object
    """
    if origin is None:
        origin = Vec3.zero()

    patch = Patch(
        patch_type=BrushType.TERRAIN,
        shader=shader,
        params=PatchParams(rows=rows, cols=cols)
    )

    for row in range(rows):
        vertex_row = []
        for col in range(cols):
            vertex = PatchVertex(
                position=Vec3(
                    origin.x + col * spacing,
                    origin.y + row * spacing,
                    origin.z
                ),
                uv=(col / (cols - 1), row / (rows - 1)) if cols > 1 and rows > 1 else (0, 0)
            )
            vertex_row.append(vertex)
        patch.vertices.append(vertex_row)

    return patch


def create_entity(classname: str, origin: Vec3 = None,
                  **properties: str) -> Entity:
    """
    Create a new entity.

    Args:
        classname: Entity classname
        origin: Entity origin (for point entities)
        **properties: Additional key-value properties

    Returns:
        Entity object
    """
    entity = Entity()
    entity.classname = classname

    if origin:
        entity.origin = origin

    for key, value in properties.items():
        entity.properties[key] = value

    return entity
