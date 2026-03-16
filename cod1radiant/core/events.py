"""
Event System for loose coupling between components.

This module implements a Publish/Subscribe pattern for communication
between GUI components without direct dependencies.

Usage:
    from cod1radiant.core.events import events, SelectionChangedEvent

    # Subscribe:
    events.subscribe(SelectionChangedEvent, self.on_selection_changed)

    # Publish:
    events.publish(SelectionChangedEvent(
        selected_brushes=frozenset({(0, 1), (0, 2)}),
        source="viewport_3d"
    ))
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable
import weakref


# =============================================================================
# Event Priority
# =============================================================================

class EventPriority(Enum):
    """Event handler priorities. Higher priority (lower value) executes first."""
    HIGH = 0      # UI updates, critical handlers
    NORMAL = 1    # Standard handlers
    LOW = 2       # Cleanup, logging


# =============================================================================
# Selection Events
# =============================================================================

@dataclass(frozen=True)
class SelectionChangedEvent:
    """
    Emitted when selection changes.

    Brushes are identified by (entity_index, brush_index) tuples.

    Attributes:
        selected_brushes: Set of (entity_idx, brush_idx) tuples
        selected_patches: Set of (entity_idx, brush_idx) tuples for patches
        selected_entities: Set of entity indices
        source: Source of the change (for loop prevention)
    """
    selected_brushes: frozenset[tuple[int, int]]
    selected_patches: frozenset[tuple[int, int]] = frozenset()
    selected_entities: frozenset[int] = frozenset()
    source: str = "unknown"


# =============================================================================
# Geometry Modified Events
# =============================================================================

@dataclass(frozen=True)
class BrushGeometryModifiedEvent:
    """
    Emitted when brush geometry is modified.

    Attributes:
        brush_ids: Set of (entity_idx, brush_idx) tuples
        modification_type: Type of modification
    """
    brush_ids: frozenset[tuple[int, int]]
    modification_type: str  # "translate", "rotate", "scale", "create", "delete", etc.


@dataclass(frozen=True)
class PatchGeometryModifiedEvent:
    """Emitted when patch geometry is modified."""
    patch_ids: frozenset[tuple[int, int]]
    modification_type: str


# =============================================================================
# Document Events
# =============================================================================

@dataclass(frozen=True)
class DocumentLoadedEvent:
    """
    Emitted when a document is loaded or created.

    Attributes:
        filepath: Path to loaded file (None for new document)
        brush_count: Number of regular brushes
        patch_count: Number of patches (terrain + curves)
        entity_count: Number of entities
    """
    filepath: str | None
    brush_count: int
    patch_count: int = 0
    entity_count: int = 0


@dataclass(frozen=True)
class DocumentModifiedEvent:
    """
    Emitted when document modified status changes.

    Attributes:
        is_modified: True if unsaved changes exist
    """
    is_modified: bool


@dataclass(frozen=True)
class DocumentClosingEvent:
    """
    Emitted before document is closed.

    Attributes:
        filepath: Path to current file (None if never saved)
    """
    filepath: str | None


# =============================================================================
# Created/Deleted Events
# =============================================================================

@dataclass(frozen=True)
class BrushCreatedEvent:
    """Emitted when a brush is created."""
    entity_index: int
    brush_index: int


@dataclass(frozen=True)
class BrushDeletedEvent:
    """Emitted when brushes are deleted."""
    brush_ids: frozenset[tuple[int, int]]


@dataclass(frozen=True)
class EntityCreatedEvent:
    """Emitted when an entity is created."""
    entity_index: int
    classname: str


@dataclass(frozen=True)
class EntityDeletedEvent:
    """Emitted when entities are deleted."""
    entity_indices: frozenset[int]


# =============================================================================
# View Events
# =============================================================================

@dataclass(frozen=True)
class ViewModeChangedEvent:
    """Emitted when 2D view mode changes."""
    axis: str  # "xy", "xz", "yz"


@dataclass(frozen=True)
class GridSizeChangedEvent:
    """Emitted when grid size changes."""
    grid_size: int


@dataclass(frozen=True)
class FilterChangedEvent:
    """Emitted when visibility filters change."""
    filters: dict[str, bool]
    visible_brush_count: int = 0
    visible_patch_count: int = 0
    visible_entity_count: int = 0


# =============================================================================
# Viewport Events
# =============================================================================

@dataclass(frozen=True)
class ViewportRefreshEvent:
    """
    Emitted when viewports should be refreshed.

    Attributes:
        source: Source of the event
        refresh_2d: True to refresh 2D viewport
        refresh_3d: True to refresh 3D viewport
        rebuild_geometry: True to rebuild geometry buffers
    """
    source: str = "unknown"
    refresh_2d: bool = True
    refresh_3d: bool = True
    rebuild_geometry: bool = False


# =============================================================================
# Other Events
# =============================================================================

@dataclass(frozen=True)
class UndoRedoEvent:
    """Emitted after undo/redo."""
    action: str  # "undo" or "redo"
    description: str


@dataclass(frozen=True)
class ToolChangedEvent:
    """Emitted when active tool changes."""
    tool_name: str
    previous_tool: str | None = None


# =============================================================================
# EventBus Implementation
# =============================================================================

class EventBus:
    """
    Central event bus for publish/subscribe communication.

    Features:
    - WeakRef-based: Prevents memory leaks
    - Priority-based execution
    - Singleton pattern
    - Pause/Resume for batch operations
    """

    _instance: "EventBus | None" = None

    def __new__(cls) -> "EventBus":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_instance()
        return cls._instance

    def _init_instance(self) -> None:
        """Initialize instance attributes."""
        self._handlers: dict[type, list[weakref.ref]] = {}
        self._handler_priorities: dict[type, list[EventPriority]] = {}
        self._paused: bool = False
        self._queued_events: list[Any] = []
        self._debug: bool = False

    @classmethod
    def get_instance(cls) -> "EventBus":
        """Singleton access."""
        return cls()

    def set_debug(self, enabled: bool) -> None:
        """Enable/disable debug logging."""
        self._debug = enabled

    def subscribe(
        self,
        event_type: type,
        handler: Callable[[Any], None],
        priority: EventPriority = EventPriority.NORMAL,
        weak: bool = True
    ) -> None:
        """
        Register a handler for an event type.

        Args:
            event_type: Event class
            handler: Callback function
            priority: Execution priority
            weak: Use WeakRef (recommended)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
            self._handler_priorities[event_type] = []

        # Create WeakRef
        if weak and hasattr(handler, '__self__'):
            ref = weakref.WeakMethod(handler)
        elif weak:
            ref = weakref.ref(handler)
        else:
            ref = lambda h=handler: h  # noqa: E731

        self._handlers[event_type].append(ref)
        self._handler_priorities[event_type].append(priority)

        self._sort_handlers(event_type)

        if self._debug:
            handler_name = getattr(handler, '__qualname__', str(handler))
            print(f"[EventBus] Subscribed {handler_name} to {event_type.__name__}")

    def _sort_handlers(self, event_type: type) -> None:
        """Sort handlers by priority."""
        pairs = list(zip(
            self._handler_priorities[event_type],
            self._handlers[event_type]
        ))
        pairs.sort(key=lambda x: x[0].value)
        self._handler_priorities[event_type] = [p for p, _ in pairs]
        self._handlers[event_type] = [h for _, h in pairs]

    def unsubscribe(self, event_type: type, handler: Callable) -> None:
        """Remove a handler."""
        if event_type not in self._handlers:
            return

        handlers = self._handlers[event_type]
        priorities = self._handler_priorities[event_type]

        for i, ref in enumerate(handlers):
            h = ref()
            if h is handler or h is None:
                handlers.pop(i)
                priorities.pop(i)
                break

    def publish(self, event: Any) -> None:
        """Publish an event to all registered handlers."""
        if self._paused:
            self._queued_events.append(event)
            return

        event_type = type(event)

        if event_type not in self._handlers:
            return

        if self._debug:
            print(f"[EventBus] Publishing {event_type.__name__}")

        handlers = self._handlers[event_type]
        priorities = self._handler_priorities[event_type]
        alive_handlers = []
        alive_priorities = []

        for ref, priority in zip(handlers, priorities):
            handler = ref()
            if handler is not None:
                alive_handlers.append(ref)
                alive_priorities.append(priority)
                try:
                    handler(event)
                except Exception as e:
                    handler_name = getattr(handler, '__qualname__', str(handler))
                    print(f"[EventBus] Error in handler {handler_name}: {e}")
                    import traceback
                    traceback.print_exc()

        self._handlers[event_type] = alive_handlers
        self._handler_priorities[event_type] = alive_priorities

    def pause(self) -> None:
        """Pause event processing."""
        self._paused = True

    def resume(self) -> None:
        """Resume event processing and process queued events."""
        self._paused = False
        queued = self._queued_events.copy()
        self._queued_events.clear()
        for event in queued:
            self.publish(event)

    def clear(self) -> None:
        """Clear all handlers."""
        self._handlers.clear()
        self._handler_priorities.clear()
        self._queued_events.clear()

    def get_handler_count(self, event_type: type) -> int:
        """Get number of live handlers for an event type."""
        if event_type not in self._handlers:
            return 0
        return sum(1 for ref in self._handlers[event_type] if ref() is not None)


# =============================================================================
# Global Instance
# =============================================================================

events = EventBus.get_instance()


__all__ = [
    # EventBus
    'EventBus',
    'events',
    'EventPriority',

    # Selection Events
    'SelectionChangedEvent',

    # Geometry Events
    'BrushGeometryModifiedEvent',
    'PatchGeometryModifiedEvent',

    # Document Events
    'DocumentLoadedEvent',
    'DocumentModifiedEvent',
    'DocumentClosingEvent',

    # Created/Deleted Events
    'BrushCreatedEvent',
    'BrushDeletedEvent',
    'EntityCreatedEvent',
    'EntityDeletedEvent',

    # View Events
    'ViewModeChangedEvent',
    'GridSizeChangedEvent',
    'FilterChangedEvent',

    # Viewport Events
    'ViewportRefreshEvent',

    # Other Events
    'UndoRedoEvent',
    'ToolChangedEvent',
]
