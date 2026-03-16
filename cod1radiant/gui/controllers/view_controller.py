"""View operations controller - Grid, Zoom, View modes."""

from __future__ import annotations
from typing import TYPE_CHECKING

from ...core.events import events, ViewModeChangedEvent, GridSizeChangedEvent
from ...config import GRID_SIZES, DEFAULT_GRID_SIZE

if TYPE_CHECKING:
    from ..main_window import MainWindow


class ViewController:
    """
    Handles view operations.

    Responsibilities:
    - Grid size management
    - View mode (xy, xz, yz)
    - Zoom controls
    - Center on selection
    """

    def __init__(self, main_window: "MainWindow") -> None:
        self._window = main_window
        self._grid_size = DEFAULT_GRID_SIZE

    # =========================================================================
    # Grid
    # =========================================================================

    @property
    def grid_size(self) -> int:
        return self._grid_size

    def set_grid_size(self, size: int) -> None:
        """Set grid size."""
        if size in GRID_SIZES:
            self._grid_size = size
            if self._window.viewport_2d is not None:
                self._window.viewport_2d.set_grid_size(size)
            events.publish(GridSizeChangedEvent(grid_size=size))

    def grid_size_up(self) -> None:
        """Increase grid size to next level."""
        try:
            idx = GRID_SIZES.index(self._grid_size)
            if idx < len(GRID_SIZES) - 1:
                self.set_grid_size(GRID_SIZES[idx + 1])
        except ValueError:
            self.set_grid_size(DEFAULT_GRID_SIZE)

    def grid_size_down(self) -> None:
        """Decrease grid size to previous level."""
        try:
            idx = GRID_SIZES.index(self._grid_size)
            if idx > 0:
                self.set_grid_size(GRID_SIZES[idx - 1])
        except ValueError:
            self.set_grid_size(DEFAULT_GRID_SIZE)

    # =========================================================================
    # View Mode
    # =========================================================================

    def set_view_mode(self, axis: str) -> None:
        """Set 2D viewport view mode."""
        if axis in ('xy', 'xz', 'yz'):
            if self._window.viewport_2d is not None:
                self._window.viewport_2d.set_axis(axis)
            events.publish(ViewModeChangedEvent(axis=axis))

    def cycle_view_mode(self) -> None:
        """Cycle through view modes."""
        if self._window.viewport_2d is None:
            return
        current = self._window.viewport_2d.axis
        modes = ['xy', 'xz', 'yz']
        try:
            idx = modes.index(current)
            next_mode = modes[(idx + 1) % len(modes)]
            self.set_view_mode(next_mode)
        except ValueError:
            self.set_view_mode('xy')

    # =========================================================================
    # Zoom & Navigation
    # =========================================================================

    def center_2d_on_selection(self) -> None:
        """Center 2D viewport on current selection."""
        if self._window.viewport_2d is not None:
            self._window.viewport_2d.center_on_selection()

    def center_3d_on_selection(self) -> None:
        """Center 3D viewport on current selection."""
        if self._window.viewport_3d is not None:
            self._window.viewport_3d.center_on_selection()

    def center_on_selection(self) -> None:
        """Center all viewports on current selection."""
        self.center_2d_on_selection()
        self.center_3d_on_selection()

    def zoom_2d_in(self) -> None:
        """Zoom in 2D viewport."""
        if self._window.viewport_2d is not None:
            self._window.viewport_2d.zoom_in()

    def zoom_2d_out(self) -> None:
        """Zoom out 2D viewport."""
        if self._window.viewport_2d is not None:
            self._window.viewport_2d.zoom_out()

    def reset_2d_view(self) -> None:
        """Reset 2D viewport to default view."""
        if self._window.viewport_2d is not None:
            self._window.viewport_2d.reset_view()
