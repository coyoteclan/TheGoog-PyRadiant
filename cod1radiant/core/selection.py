"""
Selection Manager - Manages selection state for brushes and entities.

Selection is tracked using (entity_index, brush_index) tuples for brushes,
allowing efficient lookup and modification.

Usage:
    selection = SelectionManager()

    # Select a brush
    selection.select_brush(0, 5)  # entity 0, brush 5

    # Check selection
    if selection.is_brush_selected(0, 5):
        print("Brush is selected")

    # Get all selected
    for entity_idx, brush_idx in selection.selected_brushes:
        print(f"Selected: entity {entity_idx}, brush {brush_idx}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator

from .events import events, SelectionChangedEvent

if TYPE_CHECKING:
    from ..io.map_parser.brush import Brush
    from .document import MapDocument


@dataclass
class SelectionManager:
    """
    Manages selection state for brushes, patches, and entities.

    Brushes and patches are identified by (entity_index, brush_index) tuples.
    Entities are identified by their index.

    Attributes:
        _selected_brushes: Set of selected regular brush tuples
        _selected_patches: Set of selected patch tuples
        _selected_entities: Set of selected entity indices
    """

    _selected_brushes: set[tuple[int, int]] = field(default_factory=set)
    _selected_patches: set[tuple[int, int]] = field(default_factory=set)
    _selected_entities: set[int] = field(default_factory=set)
    _selected_faces: set[tuple[int, int, int]] = field(default_factory=set)  # (entity_idx, brush_idx, face_idx)
    _suppress_events: bool = field(default=False, repr=False)

    # -------------------------------------------------------------------------
    # Brush Selection
    # -------------------------------------------------------------------------

    def select_brush(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Select a single brush."""
        key = (entity_idx, brush_idx)
        if key not in self._selected_brushes:
            self._selected_brushes.add(key)
            self._publish_change(source)

    def deselect_brush(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Deselect a single brush."""
        key = (entity_idx, brush_idx)
        if key in self._selected_brushes:
            self._selected_brushes.discard(key)
            self._publish_change(source)

    def toggle_brush(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Toggle brush selection."""
        key = (entity_idx, brush_idx)
        if key in self._selected_brushes:
            self._selected_brushes.discard(key)
        else:
            self._selected_brushes.add(key)
        self._publish_change(source)

    def is_brush_selected(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a brush is selected."""
        return (entity_idx, brush_idx) in self._selected_brushes

    def set_selected_brushes(
        self,
        brushes: set[tuple[int, int]],
        source: str = "unknown"
    ) -> None:
        """Replace entire brush selection."""
        if brushes != self._selected_brushes:
            self._selected_brushes = brushes.copy()
            self._publish_change(source)

    @property
    def selected_brushes(self) -> frozenset[tuple[int, int]]:
        """Get all selected brush tuples."""
        return frozenset(self._selected_brushes)

    @property
    def selected_brush_count(self) -> int:
        """Number of selected brushes."""
        return len(self._selected_brushes)

    # -------------------------------------------------------------------------
    # Patch Selection
    # -------------------------------------------------------------------------

    def select_patch(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Select a patch."""
        key = (entity_idx, brush_idx)
        if key not in self._selected_patches:
            self._selected_patches.add(key)
            self._publish_change(source)

    def deselect_patch(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Deselect a patch."""
        key = (entity_idx, brush_idx)
        if key in self._selected_patches:
            self._selected_patches.discard(key)
            self._publish_change(source)

    def is_patch_selected(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a patch is selected."""
        return (entity_idx, brush_idx) in self._selected_patches

    @property
    def selected_patches(self) -> frozenset[tuple[int, int]]:
        """Get all selected patch tuples."""
        return frozenset(self._selected_patches)

    # -------------------------------------------------------------------------
    # Entity Selection
    # -------------------------------------------------------------------------

    def select_entity(self, entity_idx: int, source: str = "unknown") -> None:
        """Select an entity."""
        if entity_idx not in self._selected_entities:
            self._selected_entities.add(entity_idx)
            self._publish_change(source)

    def deselect_entity(self, entity_idx: int, source: str = "unknown") -> None:
        """Deselect an entity."""
        if entity_idx in self._selected_entities:
            self._selected_entities.discard(entity_idx)
            self._publish_change(source)

    def is_entity_selected(self, entity_idx: int) -> bool:
        """Check if an entity is selected."""
        return entity_idx in self._selected_entities

    @property
    def selected_entities(self) -> frozenset[int]:
        """Get all selected entity indices."""
        return frozenset(self._selected_entities)

    # -------------------------------------------------------------------------
    # Face Selection
    # -------------------------------------------------------------------------

    def select_face(self, entity_idx: int, brush_idx: int, face_idx: int, source: str = "unknown") -> None:
        """Select a face."""
        key = (entity_idx, brush_idx, face_idx)
        if key not in self._selected_faces:
            self._selected_faces.add(key)
            self._publish_change(source)

    def deselect_face(self, entity_idx: int, brush_idx: int, face_idx: int, source: str = "unknown") -> None:
        """Deselect a face."""
        key = (entity_idx, brush_idx, face_idx)
        if key in self._selected_faces:
            self._selected_faces.discard(key)
            self._publish_change(source)

    def toggle_face(self, entity_idx: int, brush_idx: int, face_idx: int, source: str = "unknown") -> None:
        """Toggle face selection."""
        key = (entity_idx, brush_idx, face_idx)
        if key in self._selected_faces:
            self._selected_faces.discard(key)
        else:
            self._selected_faces.add(key)
        self._publish_change(source)

    def is_face_selected(self, entity_idx: int, brush_idx: int, face_idx: int) -> bool:
        """Check if a face is selected."""
        return (entity_idx, brush_idx, face_idx) in self._selected_faces

    def clear_faces(self, source: str = "unknown") -> None:
        """Clear only face selection."""
        if self._selected_faces:
            self._selected_faces.clear()
            self._publish_change(source)

    @property
    def selected_faces(self) -> frozenset[tuple[int, int, int]]:
        """Get all selected face tuples (entity_idx, brush_idx, face_idx)."""
        return frozenset(self._selected_faces)

    def get_selected_faces(self) -> list[tuple[int, int, int]]:
        """Get selected faces as a list."""
        return list(self._selected_faces)

    # -------------------------------------------------------------------------
    # Bulk Operations
    # -------------------------------------------------------------------------

    def clear(self, source: str = "unknown") -> None:
        """Clear all selections."""
        had_selection = (
            self._selected_brushes or
            self._selected_patches or
            self._selected_entities or
            self._selected_faces
        )
        self._selected_brushes.clear()
        self._selected_patches.clear()
        self._selected_entities.clear()
        self._selected_faces.clear()
        if had_selection:
            self._publish_change(source)

    def clear_brushes(self, source: str = "unknown") -> None:
        """Clear only brush selection."""
        if self._selected_brushes:
            self._selected_brushes.clear()
            self._publish_change(source)

    def select_all_brushes(
        self,
        document: "MapDocument",
        source: str = "unknown"
    ) -> None:
        """Select all brushes in the document."""
        self._selected_brushes.clear()
        for entity_idx, entity in enumerate(document.entities):
            for brush_idx, brush in enumerate(entity.brushes):
                if brush.is_regular:
                    self._selected_brushes.add((entity_idx, brush_idx))
        self._publish_change(source)

    @property
    def has_selection(self) -> bool:
        """Check if anything is selected."""
        return bool(
            self._selected_brushes or
            self._selected_patches or
            self._selected_entities or
            self._selected_faces
        )

    # -------------------------------------------------------------------------
    # Get Selected Objects
    # -------------------------------------------------------------------------

    def get_selected_brushes(self, document: "MapDocument") -> list["Brush"]:
        """
        Get actual Brush objects for all selected brushes.

        Args:
            document: The MapDocument to look up brushes from

        Returns:
            List of Brush objects
        """
        result = []
        for entity_idx, brush_idx in self._selected_brushes:
            entity = document.map_data.get_entity(entity_idx)
            if entity:
                brush = entity.get_brush(brush_idx)
                if brush and brush.is_regular:
                    result.append(brush)
        return result

    def get_selected_patches(self, document: "MapDocument") -> list["Brush"]:
        """Get actual Brush objects for all selected patches."""
        result = []
        for entity_idx, brush_idx in self._selected_patches:
            entity = document.map_data.get_entity(entity_idx)
            if entity:
                brush = entity.get_brush(brush_idx)
                if brush and brush.is_patch:
                    result.append(brush)
        return result

    def get_selected_brushes_with_keys(
        self, document: "MapDocument"
    ) -> list[tuple[tuple[int, int], "Brush"]]:
        """
        Get selected brushes with their keys.

        Args:
            document: The MapDocument to look up brushes from

        Returns:
            List of ((entity_idx, brush_idx), brush) tuples
        """
        result = []
        for entity_idx, brush_idx in self._selected_brushes:
            entity = document.map_data.get_entity(entity_idx)
            if entity:
                brush = entity.get_brush(brush_idx)
                if brush and brush.is_regular:
                    result.append(((entity_idx, brush_idx), brush))
        return result

    # -------------------------------------------------------------------------
    # Event Suppression
    # -------------------------------------------------------------------------

    def begin_batch(self) -> None:
        """Begin batch operation, suppressing events until end_batch()."""
        self._suppress_events = True

    def end_batch(self, source: str = "unknown") -> None:
        """End batch operation and publish single change event."""
        self._suppress_events = False
        self._publish_change(source)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _publish_change(self, source: str) -> None:
        """Publish selection changed event."""
        if self._suppress_events:
            return

        events.publish(SelectionChangedEvent(
            selected_brushes=frozenset(self._selected_brushes),
            selected_patches=frozenset(self._selected_patches),
            selected_entities=frozenset(self._selected_entities),
            source=source,
        ))
