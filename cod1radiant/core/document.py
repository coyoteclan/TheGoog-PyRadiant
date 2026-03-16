"""
MapDocument - Central document container for the editor.

MapDocument wraps CoD1Map and adds editor functionality:
- Selection management
- Undo/redo command stack
- Modified state tracking
- Convenience methods for geometry access

Usage:
    # Create new document
    doc = MapDocument.new()

    # Load from file
    doc = MapDocument.load("path/to/map.map")

    # Access geometry
    for brush in doc.iter_brushes():
        print(brush.get_primary_shader())

    # Modify with undo support
    doc.execute_command(TranslateBrushCommand(brush, Vec3(10, 0, 0)))
    doc.undo()

    # Save
    doc.save("output.map")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, TYPE_CHECKING

from ..io.map_parser import (
    CoD1Map,
    Entity,
    Brush,
    parse_map_file,
    create_entity,
)
from ..io.map_parser.math import Vec3

from .selection import SelectionManager
from .commands import Command, CommandStack
from .events import (
    events,
    DocumentLoadedEvent,
    DocumentModifiedEvent,
    DocumentClosingEvent,
    BrushCreatedEvent,
    BrushDeletedEvent,
    BrushGeometryModifiedEvent,
)
from .operations import compute_brush_vertices, get_brush_bounds

if TYPE_CHECKING:
    pass


@dataclass
class MapDocument:
    """
    Central document container for the editor.

    Wraps CoD1Map and provides editor functionality including
    selection, undo/redo, and modification tracking.

    Attributes:
        map_data: The underlying CoD1Map
        filepath: Path to the loaded file (None if new)
        selection: Selection state manager
        command_stack: Undo/redo stack
        modified: True if document has unsaved changes
    """

    map_data: CoD1Map
    filepath: Path | None = None
    selection: SelectionManager = field(default_factory=SelectionManager)
    command_stack: CommandStack = field(default_factory=CommandStack)
    modified: bool = False

    # Vertex cache: (entity_idx, brush_idx) -> face_vertices dict
    _vertex_cache: dict[tuple[int, int], dict[int, list[Vec3]]] = field(
        default_factory=dict, repr=False
    )

    # -------------------------------------------------------------------------
    # Factory Methods
    # -------------------------------------------------------------------------

    @classmethod
    def new(cls) -> "MapDocument":
        """
        Create a new empty document with worldspawn.

        Returns:
            New MapDocument with empty worldspawn entity
        """
        map_data = CoD1Map()

        # Create worldspawn entity
        worldspawn = create_entity("worldspawn")
        map_data.add_entity(worldspawn)

        doc = cls(map_data=map_data)

        events.publish(DocumentLoadedEvent(
            filepath=None,
            brush_count=0,
            patch_count=0,
            entity_count=1,
        ))

        return doc

    @classmethod
    def load(cls, filepath: str | Path) -> "MapDocument":
        """
        Load a document from a .map file.

        Args:
            filepath: Path to the .map file

        Returns:
            Loaded MapDocument

        Raises:
            FileNotFoundError: If file doesn't exist
            ParseError: If file is invalid
        """
        filepath = Path(filepath)
        map_data = parse_map_file(str(filepath))

        doc = cls(map_data=map_data, filepath=filepath)

        # Count geometry
        brush_count = 0
        patch_count = 0
        for entity in map_data.entities:
            for brush in entity.brushes:
                if brush.is_regular:
                    brush_count += 1
                else:
                    patch_count += 1

        events.publish(DocumentLoadedEvent(
            filepath=str(filepath),
            brush_count=brush_count,
            patch_count=patch_count,
            entity_count=map_data.entity_count,
        ))

        return doc

    # -------------------------------------------------------------------------
    # Save
    # -------------------------------------------------------------------------

    def save(self, filepath: str | Path | None = None) -> None:
        """
        Save the document to a .map file.

        Args:
            filepath: Path to save to (uses current filepath if None)

        Raises:
            ValueError: If no filepath specified and document was never saved
        """
        if filepath is None:
            if self.filepath is None:
                raise ValueError("No filepath specified and document has never been saved")
            filepath = self.filepath
        else:
            filepath = Path(filepath)

        self.map_data.save(str(filepath))
        self.filepath = filepath
        self._set_modified(False)

    # -------------------------------------------------------------------------
    # Convenience Properties
    # -------------------------------------------------------------------------

    @property
    def worldspawn(self) -> Entity | None:
        """Get the worldspawn entity."""
        return self.map_data.worldspawn

    @property
    def entities(self) -> list[Entity]:
        """Get all entities."""
        return self.map_data.entities

    @property
    def entity_count(self) -> int:
        """Number of entities."""
        return self.map_data.entity_count

    # -------------------------------------------------------------------------
    # Geometry Iteration
    # -------------------------------------------------------------------------

    def iter_brushes(self) -> Iterator[tuple[int, int, Brush]]:
        """
        Iterate over all regular brushes.

        Yields:
            (entity_index, brush_index, brush) tuples
        """
        for entity_idx, entity in enumerate(self.entities):
            for brush_idx, brush in enumerate(entity.brushes):
                if brush.is_regular:
                    yield entity_idx, brush_idx, brush

    def iter_patches(self) -> Iterator[tuple[int, int, Brush]]:
        """
        Iterate over all patches (terrain and curves).

        Yields:
            (entity_index, brush_index, brush) tuples
        """
        for entity_idx, entity in enumerate(self.entities):
            for brush_idx, brush in enumerate(entity.brushes):
                if brush.is_patch:
                    yield entity_idx, brush_idx, brush

    def iter_all_geometry(self) -> Iterator[tuple[int, int, Brush]]:
        """
        Iterate over all brushes and patches.

        Yields:
            (entity_index, brush_index, brush) tuples
        """
        for entity_idx, entity in enumerate(self.entities):
            for brush_idx, brush in enumerate(entity.brushes):
                yield entity_idx, brush_idx, brush

    def iter_point_entities(self) -> Iterator[tuple[int, Entity]]:
        """
        Iterate over point entities (no geometry).

        Yields:
            (entity_index, entity) tuples
        """
        for entity_idx, entity in enumerate(self.entities):
            if entity.is_point_entity:
                yield entity_idx, entity

    # -------------------------------------------------------------------------
    # Geometry Access
    # -------------------------------------------------------------------------

    def get_brush(self, entity_idx: int, brush_idx: int) -> Brush | None:
        """Get a specific brush by indices."""
        entity = self.map_data.get_entity(entity_idx)
        if entity:
            return entity.get_brush(brush_idx)
        return None

    def get_entity(self, entity_idx: int) -> Entity | None:
        """Get a specific entity by index."""
        return self.map_data.get_entity(entity_idx)

    def get_all_brushes(self) -> list[Brush]:
        """Get all regular brushes as a flat list."""
        return [brush for _, _, brush in self.iter_brushes()]

    def get_all_patches(self) -> list[Brush]:
        """Get all patches as a flat list."""
        return [brush for _, _, brush in self.iter_patches()]

    def get_selected_brushes(self) -> list[Brush]:
        """
        Get all currently selected brushes.

        Convenience method that delegates to SelectionManager.

        Returns:
            List of selected Brush objects
        """
        return self.selection.get_selected_brushes(self)

    def get_selected_patches(self) -> list[Brush]:
        """
        Get all currently selected patches.

        Convenience method that delegates to SelectionManager.

        Returns:
            List of selected Brush (patch) objects
        """
        return self.selection.get_selected_patches(self)

    # -------------------------------------------------------------------------
    # Vertex Cache
    # -------------------------------------------------------------------------

    def get_brush_vertices(
        self,
        entity_idx: int,
        brush_idx: int
    ) -> dict[int, list[Vec3]]:
        """
        Get computed vertices for a brush.

        Uses cache for performance. Call invalidate_brush_cache() after
        modifying brush geometry.

        Args:
            entity_idx: Entity index
            brush_idx: Brush index

        Returns:
            Dict mapping face index to vertex list
        """
        key = (entity_idx, brush_idx)
        if key not in self._vertex_cache:
            brush = self.get_brush(entity_idx, brush_idx)
            if brush and brush.is_regular:
                self._vertex_cache[key] = compute_brush_vertices(brush)
            else:
                self._vertex_cache[key] = {}
        return self._vertex_cache[key]

    def invalidate_brush_cache(self, entity_idx: int, brush_idx: int) -> None:
        """Invalidate cached vertices for a brush."""
        key = (entity_idx, brush_idx)
        self._vertex_cache.pop(key, None)

    def invalidate_all_caches(self) -> None:
        """Invalidate all cached vertices."""
        self._vertex_cache.clear()

    # -------------------------------------------------------------------------
    # Brush Modification
    # -------------------------------------------------------------------------

    def add_brush_to_worldspawn(self, brush: Brush) -> tuple[int, int] | None:
        """
        Add a brush to the worldspawn entity.

        Args:
            brush: The brush to add

        Returns:
            (entity_idx, brush_idx) tuple or None if no worldspawn
        """
        if self.worldspawn is None:
            return None

        self.worldspawn.add_brush(brush)
        entity_idx = 0  # Worldspawn is always entity 0
        brush_idx = brush.index

        self._set_modified(True)

        events.publish(BrushCreatedEvent(
            entity_index=entity_idx,
            brush_index=brush_idx,
        ))

        return entity_idx, brush_idx

    def remove_brush(self, entity_idx: int, brush_idx: int) -> Brush | None:
        """
        Remove a brush from an entity.

        Args:
            entity_idx: Entity index
            brush_idx: Brush index

        Returns:
            Removed brush or None if not found
        """
        entity = self.get_entity(entity_idx)
        if entity is None:
            return None

        brush = entity.remove_brush(brush_idx)
        if brush:
            self.invalidate_brush_cache(entity_idx, brush_idx)
            self._set_modified(True)

            events.publish(BrushDeletedEvent(
                brush_ids=frozenset({(entity_idx, brush_idx)}),
            ))

        return brush

    def notify_brush_modified(
        self,
        entity_idx: int,
        brush_idx: int,
        modification_type: str = "edit"
    ) -> None:
        """
        Notify that a brush was modified.

        Call after modifying brush geometry to update caches and UI.

        Args:
            entity_idx: Entity index
            brush_idx: Brush index
            modification_type: Type of modification
        """
        self.invalidate_brush_cache(entity_idx, brush_idx)
        self._set_modified(True)

        events.publish(BrushGeometryModifiedEvent(
            brush_ids=frozenset({(entity_idx, brush_idx)}),
            modification_type=modification_type,
        ))

    # -------------------------------------------------------------------------
    # Entity Operations
    # -------------------------------------------------------------------------

    def add_entity(self, entity: Entity) -> int:
        """
        Add an entity to the map.

        Args:
            entity: The entity to add

        Returns:
            Index of the added entity
        """
        self.map_data.add_entity(entity)
        self._set_modified(True)
        return entity.index

    def remove_entity(self, entity_idx: int) -> Entity | None:
        """
        Remove an entity from the map.

        Cannot remove worldspawn (entity 0).

        Args:
            entity_idx: Entity index

        Returns:
            Removed entity or None
        """
        entity = self.map_data.remove_entity(entity_idx)
        if entity:
            self._set_modified(True)
        return entity

    # -------------------------------------------------------------------------
    # Command Stack
    # -------------------------------------------------------------------------

    def execute_command(self, command: Command) -> None:
        """Execute a command with undo support."""
        self.command_stack.execute(command)
        self._set_modified(True)

    def undo(self) -> bool:
        """Undo the last command."""
        if self.command_stack.undo():
            self._set_modified(True)
            return True
        return False

    def redo(self) -> bool:
        """Redo the last undone command."""
        if self.command_stack.redo():
            self._set_modified(True)
            return True
        return False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.command_stack.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.command_stack.can_redo()

    # -------------------------------------------------------------------------
    # Document State
    # -------------------------------------------------------------------------

    def _set_modified(self, modified: bool) -> None:
        """Set modified state and publish event if changed."""
        if self.modified != modified:
            self.modified = modified
            events.publish(DocumentModifiedEvent(is_modified=modified))

    def close(self) -> None:
        """Close the document, publishing closing event."""
        events.publish(DocumentClosingEvent(
            filepath=str(self.filepath) if self.filepath else None,
        ))
        self.selection.clear()
        self.command_stack.clear()
        self._vertex_cache.clear()

    # -------------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------------

    def get_statistics(self) -> dict:
        """Get document statistics."""
        brush_count = 0
        patch_count = 0
        terrain_count = 0
        curve_count = 0

        for _, _, brush in self.iter_all_geometry():
            if brush.is_regular:
                brush_count += 1
            elif brush.is_terrain:
                terrain_count += 1
                patch_count += 1
            elif brush.is_curve:
                curve_count += 1
                patch_count += 1

        point_entities = sum(1 for _ in self.iter_point_entities())

        return {
            "entity_count": self.entity_count,
            "brush_count": brush_count,
            "patch_count": patch_count,
            "terrain_count": terrain_count,
            "curve_count": curve_count,
            "point_entity_count": point_entities,
            "unique_shaders": len(self.map_data.get_all_shaders()),
        }
