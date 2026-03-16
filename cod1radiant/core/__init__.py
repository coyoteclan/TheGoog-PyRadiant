"""
CoD1 Radiant Core Module - Built on the new Parser
===================================================

This module provides all core functionality for the CoD1 Radiant editor,
built on the clean parser classes from io/map_parser.

Core Classes:
- Vec3, Color: 3D math primitives
- BrushPlane, Brush: Brush geometry
- Patch, PatchVertex: Curve/terrain patches
- Entity: Map entities with properties and geometry
- CoD1Map: Complete map container

Editor Classes:
- MapDocument: Editor wrapper around CoD1Map
- SelectionManager: Selection state management
- CommandStack: Undo/redo system

Operations:
- compute_brush_vertices(): Calculate vertices from planes
- get_brush_bounds(): Calculate bounding box
- intersect_ray_brush(): Ray-brush intersection for picking

Usage:
    from cod1radiant.core import (
        MapDocument, Vec3, Brush, Entity,
        parse_map_file, create_brush_box
    )

    # Load a map
    doc = MapDocument.load("map.map")

    # Access geometry
    for brush in doc.iter_brushes():
        vertices = brush.get_face_vertices(0)
        print(vertices)

    # Create new geometry
    brush = create_brush_box(Vec3(0, 0, 0), Vec3(64, 64, 64))
    doc.add_brush_to_worldspawn(brush)

    # Save
    doc.save("output.map")
"""

# Import from the new parser package (using absolute imports to avoid io/__init__ issues)
import cod1radiant.io.map_parser.math as _math
import cod1radiant.io.map_parser.types as _types
import cod1radiant.io.map_parser.brush as _brush
import cod1radiant.io.map_parser.patch as _patch
import cod1radiant.io.map_parser.entity as _entity
import cod1radiant.io.map_parser.map as _map
import cod1radiant.io.map_parser.parser as _parser

# Math primitives
Vec3 = _math.Vec3
Color = _math.Color

# Type definitions
BrushType = _types.BrushType
ContentFlag = _types.ContentFlag
TextureParams = _types.TextureParams
PatchParams = _types.PatchParams
TOOL_SHADERS = _types.TOOL_SHADERS

# Geometry classes
BrushPlane = _brush.BrushPlane
Brush = _brush.Brush
PatchVertex = _patch.PatchVertex
Patch = _patch.Patch
Entity = _entity.Entity

# Map container and helpers
CoD1Map = _map.CoD1Map
create_brush_box = _map.create_brush_box
create_terrain_patch = _map.create_terrain_patch
create_entity = _map.create_entity

# Parser functions
CoD1MapParser = _parser.CoD1MapParser
parse_map_file = _parser.parse_map_file
parse_map_string = _parser.parse_map_string

# Operations
from .operations import (
    compute_brush_vertices,
    get_brush_bounds,
    get_brush_center,
    get_all_brush_vertices,
    is_brush_valid,
    intersect_ray_brush,
    get_face_center,
    get_face_normal,
)

# Primitives
from .primitives import (
    create_block,
    create_cylinder,
    create_cone,
    create_wedge,
    create_spike,
    create_pyramid,
)

# Editor classes
from .document import MapDocument
from .selection import SelectionManager
from .commands import (
    Command,
    CommandStack,
    TranslateBrushCommand,
    DeleteBrushCommand,
    CreateBrushCommand,
    CompoundCommand,
)
from .events import (
    EventBus,
    events,
    EventPriority,
    SelectionChangedEvent,
    BrushGeometryModifiedEvent,
    PatchGeometryModifiedEvent,
    DocumentLoadedEvent,
    DocumentModifiedEvent,
    DocumentClosingEvent,
    BrushCreatedEvent,
    BrushDeletedEvent,
    EntityCreatedEvent,
    EntityDeletedEvent,
    ViewModeChangedEvent,
    GridSizeChangedEvent,
    FilterChangedEvent,
    ViewportRefreshEvent,
    UndoRedoEvent,
    ToolChangedEvent,
)

# UI State
from .ui_state import (
    UIStateManager,
    ui_state,
    ObjectType,
    VisibilityChangedEvent,
)

# Entity Definitions
from .entity_defs import (
    EntityDef,
    PropertyDef,
    get_entity_def,
    get_all_classnames,
    get_point_entity_classnames,
    get_brush_entity_classnames,
    get_entity_color,
    get_entity_size,
    ENTITY_DEFINITIONS,
)

# Texture Manager
from .texture_manager import (
    TextureManager,
    TextureInfo,
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

    # Geometry
    'BrushPlane',
    'Brush',
    'PatchVertex',
    'Patch',
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

    # Operations
    'compute_brush_vertices',
    'get_brush_bounds',
    'get_brush_center',
    'get_all_brush_vertices',
    'is_brush_valid',
    'intersect_ray_brush',
    'get_face_center',
    'get_face_normal',

    # Primitives
    'create_block',
    'create_cylinder',
    'create_cone',
    'create_wedge',
    'create_spike',
    'create_pyramid',

    # Editor
    'MapDocument',
    'SelectionManager',
    'Command',
    'CommandStack',
    'TranslateBrushCommand',
    'DeleteBrushCommand',
    'CreateBrushCommand',
    'CompoundCommand',

    # Events
    'EventBus',
    'events',
    'EventPriority',
    'SelectionChangedEvent',
    'BrushGeometryModifiedEvent',
    'PatchGeometryModifiedEvent',
    'DocumentLoadedEvent',
    'DocumentModifiedEvent',
    'DocumentClosingEvent',
    'BrushCreatedEvent',
    'BrushDeletedEvent',
    'EntityCreatedEvent',
    'EntityDeletedEvent',
    'ViewModeChangedEvent',
    'GridSizeChangedEvent',
    'FilterChangedEvent',
    'ViewportRefreshEvent',
    'UndoRedoEvent',
    'ToolChangedEvent',

    # UI State
    'UIStateManager',
    'ui_state',
    'ObjectType',
    'VisibilityChangedEvent',

    # Entity Definitions
    'EntityDef',
    'PropertyDef',
    'get_entity_def',
    'get_all_classnames',
    'get_point_entity_classnames',
    'get_brush_entity_classnames',
    'get_entity_color',
    'get_entity_size',
    'ENTITY_DEFINITIONS',

    # Texture Manager
    'TextureManager',
    'TextureInfo',
]
