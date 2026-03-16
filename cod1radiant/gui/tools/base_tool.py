"""Base class for 2D viewport tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Protocol

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter

if TYPE_CHECKING:
    from ..viewport_2d import Viewport2DGL
    from ...core import Brush, MapDocument


class EditMode(Enum):
    """Edit modes for the 2D viewport."""
    RESIZE = auto()  # Default mode - resize handles on selection bounds
    EDGE = auto()    # Edge mode - vertex/edge handles on brush geometry


class ViewportContext(Protocol):
    """Protocol defining what the viewport provides to tools."""

    document: "MapDocument"
    axis: str
    grid_size: int
    zoom: float

    def world_to_screen(self, wx: float, wy: float): ...
    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]: ...
    def update(self) -> None: ...
    def setCursor(self, cursor) -> None: ...


class BaseTool(ABC):
    """Base class for 2D viewport tools."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport

    @property
    def document(self) -> "MapDocument":
        return self.viewport.document

    @property
    def grid_size(self) -> int:
        return self.viewport.grid_size

    @property
    def zoom(self) -> float:
        return self.viewport.zoom

    def _get_axes(self) -> tuple[int, int]:
        """Get the world axis indices for this viewport."""
        if self.viewport.axis == 'xy':
            return (0, 1)
        elif self.viewport.axis == 'xz':
            return (0, 2)
        else:  # yz
            return (1, 2)

    def world_to_screen(self, wx: float, wy: float):
        """Convert world coordinates to screen coordinates."""
        return self.viewport.world_to_screen(wx, wy)

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        return self.viewport.screen_to_world(sx, sy)

    def snap_to_grid(self, value: float) -> float:
        """Snap a value to the grid."""
        return round(value / self.grid_size) * self.grid_size

    def _show_status(self, message: str, timeout: int = 2000):
        """Show a status message in the main window."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'statusBar'):
                parent.statusBar().showMessage(message, timeout)
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _log_console(self, message: str, level: str = "info"):
        """Log a message to the Radiant console."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'log_message'):
                parent.log_message(message, level)
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _notify_3d_viewport(self):
        """Notify 3D viewport to update."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'viewport_3d'):
                parent.viewport_3d.update()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _rebuild_3d_geometry(self):
        """Tell the 3D viewport to rebuild geometry for moved brushes."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'viewport_3d'):
                parent.viewport_3d._rebuild_moved_brushes()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _rebuild_all_3d_geometry(self):
        """Tell the 3D viewport to rebuild all geometry."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'viewport_3d'):
                parent.viewport_3d.set_document(self.document)
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _rebuild_2d_geometry(self):
        """Tell the 2D viewport to rebuild geometry (for ModernGL viewport)."""
        # New modular structure: geometry_builder handles dirty flag
        if hasattr(self.viewport, '_geometry_builder') and self.viewport._geometry_builder:
            self.viewport._geometry_builder.mark_dirty()
        # Legacy fallback
        elif hasattr(self.viewport, '_geometry_dirty'):
            self.viewport._geometry_dirty = True
        self.viewport.update()

    def _rebuild_all_geometry(self):
        """Rebuild geometry in both 2D and 3D viewports."""
        self._rebuild_2d_geometry()
        self._rebuild_all_3d_geometry()

    # Abstract methods that tools must implement
    @abstractmethod
    def draw(self, painter: QPainter) -> None:
        """Draw tool-specific visuals."""
        pass

    @abstractmethod
    def get_handle_at(self, sx: float, sy: float) -> object | None:
        """Get handle at screen coordinates, or None."""
        pass

    @abstractmethod
    def start_drag(self, handle: object, wx: float, wy: float) -> None:
        """Start dragging a handle."""
        pass

    @abstractmethod
    def update_drag(self, wx: float, wy: float) -> None:
        """Update during drag."""
        pass

    @abstractmethod
    def end_drag(self) -> None:
        """End dragging."""
        pass

    @abstractmethod
    def is_dragging(self) -> bool:
        """Return True if currently dragging."""
        pass

    def get_cursor_for_handle(self, handle: object) -> Qt.CursorShape:
        """Get the appropriate cursor for a handle."""
        return Qt.CursorShape.SizeAllCursor
