"""
File I/O module for loading and saving CoD1 .map files.

This module provides the parser for CoD1 map format:
- parse_map_file(): Load a map file
- CoD1Map: Container for the entire map with save() method
- Brush, Entity, Patch: Geometry classes
- Vec3, Color: Math primitives

Usage:
    from cod1radiant.io import parse_map_file, CoD1Map, Brush, Entity

    # Load a map
    map_data = parse_map_file("path/to/map.map")

    # Access entities and brushes
    for entity in map_data.entities:
        print(entity.classname)
        for brush in entity.brushes:
            print(brush.get_primary_shader())

    # Save a map
    map_data.save("output.map")
"""

from .map_parser import (
    # Core classes
    CoD1Map,
    Entity,
    Brush,
    BrushPlane,
    Patch,
    PatchVertex,

    # Math primitives
    Vec3,
    Color,

    # Type definitions
    BrushType,
    TextureParams,
    PatchParams,
    ContentFlag,

    # Parser functions
    parse_map_file,
    parse_map_string,
    CoD1MapParser,

    # Creation helpers
    create_brush_box,
    create_terrain_patch,
    create_entity,
)

__all__ = [
    # Core classes
    "CoD1Map",
    "Entity",
    "Brush",
    "BrushPlane",
    "Patch",
    "PatchVertex",

    # Math primitives
    "Vec3",
    "Color",

    # Type definitions
    "BrushType",
    "TextureParams",
    "PatchParams",
    "ContentFlag",

    # Parser functions
    "parse_map_file",
    "parse_map_string",
    "CoD1MapParser",

    # Creation helpers
    "create_brush_box",
    "create_terrain_patch",
    "create_entity",
]
