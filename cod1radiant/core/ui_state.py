"""
UI State Manager - Separation of UI state from data.

This module manages UI-specific states (hidden, locked) separately
from data classes. Uses index-based object identification (entity_idx, brush_idx).
"""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

from .events import events

if TYPE_CHECKING:
    pass


# =============================================================================
# Object Types
# =============================================================================

class ObjectType(Enum):
    """Types of objects managed in UI state."""
    BRUSH = auto()      # Regular brushes: (entity_idx, brush_idx)
    PATCH = auto()      # Patches (terrain/curves): (entity_idx, brush_idx)
    ENTITY = auto()     # Entities: entity_idx


# =============================================================================
# Visibility Changed Event
# =============================================================================

from dataclasses import dataclass

@dataclass(frozen=True)
class VisibilityChangedEvent:
    """
    Emitted when object visibility changes.

    Attributes:
        hidden_brushes: Set of hidden brush indices (entity_idx, brush_idx)
        hidden_patches: Set of hidden patch indices (entity_idx, brush_idx)
        hidden_entities: Set of hidden entity indices
        source: Source of the change
    """
    hidden_brushes: frozenset[tuple[int, int]]
    hidden_patches: frozenset[tuple[int, int]] = frozenset()
    hidden_entities: frozenset[int] = frozenset()
    source: str = "unknown"


# =============================================================================
# UIStateManager
# =============================================================================

class UIStateManager:
    """
    Manages UI-specific states for all objects.

    Uses index-based identification:
    - Brushes/Patches: (entity_idx, brush_idx) tuples
    - Entities: entity_idx integers

    Example:
        ui_state = UIStateManager()

        # Hide a brush
        ui_state.hide_brush(0, 1)  # entity 0, brush 1

        # Check if hidden
        if ui_state.is_brush_hidden(0, 1):
            continue  # Skip rendering

        # Get all hidden brushes
        hidden = ui_state.hidden_brushes
    """

    _instance: "UIStateManager | None" = None

    def __new__(cls) -> "UIStateManager":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance()
        return cls._instance

    def _init_instance(self) -> None:
        """Initialize instance attributes."""
        # Hidden sets using index tuples
        self._hidden_brushes: set[tuple[int, int]] = set()
        self._hidden_patches: set[tuple[int, int]] = set()
        self._hidden_entities: set[int] = set()

    @classmethod
    def get_instance(cls) -> "UIStateManager":
        """Get singleton instance."""
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (for tests)."""
        cls._instance = None

    # =========================================================================
    # Brush Visibility
    # =========================================================================

    def hide_brush(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Hide a brush."""
        key = (entity_idx, brush_idx)
        if key not in self._hidden_brushes:
            self._hidden_brushes.add(key)
            self._notify_visibility_change(source)

    def show_brush(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Show a hidden brush."""
        key = (entity_idx, brush_idx)
        if key in self._hidden_brushes:
            self._hidden_brushes.discard(key)
            self._notify_visibility_change(source)

    def toggle_brush_hidden(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Toggle brush visibility."""
        key = (entity_idx, brush_idx)
        if key in self._hidden_brushes:
            self._hidden_brushes.discard(key)
        else:
            self._hidden_brushes.add(key)
        self._notify_visibility_change(source)

    def is_brush_hidden(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a brush is hidden."""
        return (entity_idx, brush_idx) in self._hidden_brushes

    def is_brush_visible(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a brush is visible."""
        return (entity_idx, brush_idx) not in self._hidden_brushes

    @property
    def hidden_brushes(self) -> frozenset[tuple[int, int]]:
        """Get all hidden brush indices."""
        return frozenset(self._hidden_brushes)

    # =========================================================================
    # Patch Visibility
    # =========================================================================

    def hide_patch(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Hide a patch."""
        key = (entity_idx, brush_idx)
        if key not in self._hidden_patches:
            self._hidden_patches.add(key)
            self._notify_visibility_change(source)

    def show_patch(self, entity_idx: int, brush_idx: int, source: str = "unknown") -> None:
        """Show a hidden patch."""
        key = (entity_idx, brush_idx)
        if key in self._hidden_patches:
            self._hidden_patches.discard(key)
            self._notify_visibility_change(source)

    def is_patch_hidden(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a patch is hidden."""
        return (entity_idx, brush_idx) in self._hidden_patches

    def is_patch_visible(self, entity_idx: int, brush_idx: int) -> bool:
        """Check if a patch is visible."""
        return (entity_idx, brush_idx) not in self._hidden_patches

    @property
    def hidden_patches(self) -> frozenset[tuple[int, int]]:
        """Get all hidden patch indices."""
        return frozenset(self._hidden_patches)

    # =========================================================================
    # Entity Visibility
    # =========================================================================

    def hide_entity(self, entity_idx: int, source: str = "unknown") -> None:
        """Hide an entity."""
        if entity_idx not in self._hidden_entities:
            self._hidden_entities.add(entity_idx)
            self._notify_visibility_change(source)

    def show_entity(self, entity_idx: int, source: str = "unknown") -> None:
        """Show a hidden entity."""
        if entity_idx in self._hidden_entities:
            self._hidden_entities.discard(entity_idx)
            self._notify_visibility_change(source)

    def is_entity_hidden(self, entity_idx: int) -> bool:
        """Check if an entity is hidden."""
        return entity_idx in self._hidden_entities

    def is_entity_visible(self, entity_idx: int) -> bool:
        """Check if an entity is visible."""
        return entity_idx not in self._hidden_entities

    @property
    def hidden_entities(self) -> frozenset[int]:
        """Get all hidden entity indices."""
        return frozenset(self._hidden_entities)

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def hide_brushes(self, brush_ids: set[tuple[int, int]], source: str = "unknown") -> None:
        """Hide multiple brushes at once."""
        before = len(self._hidden_brushes)
        self._hidden_brushes.update(brush_ids)
        if len(self._hidden_brushes) > before:
            self._notify_visibility_change(source)

    def show_brushes(self, brush_ids: set[tuple[int, int]], source: str = "unknown") -> None:
        """Show multiple brushes at once."""
        before = len(self._hidden_brushes)
        self._hidden_brushes -= brush_ids
        if len(self._hidden_brushes) < before:
            self._notify_visibility_change(source)

    def show_all(self, source: str = "unknown") -> None:
        """Show all hidden objects."""
        changed = bool(self._hidden_brushes or self._hidden_patches or self._hidden_entities)
        self._hidden_brushes.clear()
        self._hidden_patches.clear()
        self._hidden_entities.clear()
        if changed:
            self._notify_visibility_change(source)

    def show_all_brushes(self, source: str = "unknown") -> None:
        """Show all hidden brushes."""
        if self._hidden_brushes:
            self._hidden_brushes.clear()
            self._notify_visibility_change(source)

    def show_all_patches(self, source: str = "unknown") -> None:
        """Show all hidden patches."""
        if self._hidden_patches:
            self._hidden_patches.clear()
            self._notify_visibility_change(source)

    def show_all_entities(self, source: str = "unknown") -> None:
        """Show all hidden entities."""
        if self._hidden_entities:
            self._hidden_entities.clear()
            self._notify_visibility_change(source)

    # =========================================================================
    # Cleanup
    # =========================================================================

    def clear(self, source: str = "unknown") -> None:
        """Clear all UI state (e.g., for new document)."""
        changed = bool(self._hidden_brushes or self._hidden_patches or self._hidden_entities)
        self._hidden_brushes.clear()
        self._hidden_patches.clear()
        self._hidden_entities.clear()
        if changed:
            self._notify_visibility_change(source)

    def remove_deleted_brush(self, entity_idx: int, brush_idx: int) -> None:
        """Remove a deleted brush from state."""
        self._hidden_brushes.discard((entity_idx, brush_idx))

    def remove_deleted_entity(self, entity_idx: int) -> None:
        """Remove a deleted entity and its brushes from state."""
        self._hidden_entities.discard(entity_idx)
        # Remove all brushes belonging to this entity
        self._hidden_brushes = {
            (e, b) for e, b in self._hidden_brushes if e != entity_idx
        }
        self._hidden_patches = {
            (e, b) for e, b in self._hidden_patches if e != entity_idx
        }

    # =========================================================================
    # Event Publishing
    # =========================================================================

    def _notify_visibility_change(self, source: str) -> None:
        """Publish VisibilityChangedEvent."""
        events.publish(VisibilityChangedEvent(
            hidden_brushes=frozenset(self._hidden_brushes),
            hidden_patches=frozenset(self._hidden_patches),
            hidden_entities=frozenset(self._hidden_entities),
            source=source
        ))

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> dict[str, int]:
        """Get statistics about UI state."""
        return {
            'hidden_brushes': len(self._hidden_brushes),
            'hidden_patches': len(self._hidden_patches),
            'hidden_entities': len(self._hidden_entities),
        }


# =============================================================================
# Global Instance
# =============================================================================

ui_state = UIStateManager.get_instance()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'UIStateManager',
    'ui_state',
    'ObjectType',
    'VisibilityChangedEvent',
]
