"""
CoD1 Map Parser Package
=======================

Complete parser for the Call of Duty 1 .map file format.
All map elements are fully addressable and modifiable.

Usage:
    from cod1_map import parse_map_file, CoD1Map, Vec3

    # Parse a map file
    map_data = parse_map_file("path/to/map.map")

    # Access elements
    worldspawn = map_data.worldspawn
    for brush in worldspawn.brushes:
        if brush.is_terrain:
            patch = brush.patch
            for row in range(patch.rows):
                for col in range(patch.cols):
                    vertex = patch.get_vertex(row, col)
                    vertex.position.z += 10

    # Save modified map
    map_data.save("output.map")

Module Structure:
    cod1_map/
    ├── __init__.py     # Package exports
    ├── math.py         # Vec3, Color
    ├── types.py        # Enums, TextureParams, PatchParams
    ├── patch.py        # PatchVertex, Patch
    ├── brush.py        # BrushPlane, Brush
    ├── entity.py       # Entity
    ├── map.py          # CoD1Map, helper functions
    └── parser.py       # CoD1MapParser, parse functions
"""

# Math
from .math import Vec3, Color

# Types
from .types import (
    BrushType,
    ContentFlag,
    TextureParams,
    PatchParams,
    TOOL_SHADERS,
)

# Patch
from .patch import PatchVertex, Patch

# Brush
from .brush import BrushPlane, Brush

# Entity
from .entity import Entity

# Map
from .map import (
    CoD1Map,
    create_brush_box,
    create_terrain_patch,
    create_entity,
)

# Parser
from .parser import (
    CoD1MapParser,
    parse_map_file,
    parse_map_string,
)


__all__ = [
    # Math
    'Vec3',
    'Color',

    # Types
    'BrushType',
    'ContentFlag',
    'TextureParams',
    'PatchParams',
    'TOOL_SHADERS',

    # Patch
    'PatchVertex',
    'Patch',

    # Brush
    'BrushPlane',
    'Brush',

    # Entity
    'Entity',

    # Map
    'CoD1Map',
    'create_brush_box',
    'create_terrain_patch',
    'create_entity',

    # Parser
    'CoD1MapParser',
    'parse_map_file',
    'parse_map_string',
]

__version__ = '1.0.0'
