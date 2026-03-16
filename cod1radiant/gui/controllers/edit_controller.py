"""Edit operations controller - Undo, Redo, Selection, Delete, Duplicate."""

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

from ...core import (
    events,
    BrushGeometryModifiedEvent,
    BrushDeletedEvent,
    UndoRedoEvent,
    Vec3,
    get_brush_center,
)

if TYPE_CHECKING:
    from ..main_window import MainWindow
    from ...core import MapDocument


class EditController:
    """
    Handles edit operations.

    Responsibilities:
    - Undo/Redo
    - Selection management
    - Delete, Duplicate
    - Transform operations (rotate, scale)
    """

    def __init__(self, main_window: "MainWindow") -> None:
        self._window = main_window

    @property
    def document(self) -> "MapDocument":
        return self._window.document

    # =========================================================================
    # Undo/Redo
    # =========================================================================

    def undo(self) -> bool:
        """Undo last action."""
        description = self.document.command_stack.get_undo_description()

        if self.document.undo():
            events.publish(UndoRedoEvent(action="undo", description=description))

            # Trigger geometry refresh
            events.publish(BrushGeometryModifiedEvent(
                brush_ids=frozenset(),
                modification_type="undo"
            ))
            return True
        return False

    def redo(self) -> bool:
        """Redo last undone action."""
        description = self.document.command_stack.get_redo_description()

        if self.document.redo():
            events.publish(UndoRedoEvent(action="redo", description=description))

            events.publish(BrushGeometryModifiedEvent(
                brush_ids=frozenset(),
                modification_type="redo"
            ))
            return True
        return False

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.document.command_stack.can_undo()

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.document.command_stack.can_redo()

    # =========================================================================
    # Selection
    # =========================================================================

    def deselect_all(self, source: str = "edit_controller") -> None:
        """Clear all selection."""
        self.document.selection.clear(source=source)

    def select_all_brushes(self, source: str = "edit_controller") -> None:
        """Select all brushes."""
        for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
            if brush.is_regular:
                self.document.selection.select_brush(entity_idx, brush_idx, source=source)

    def select_all(self, source: str = "edit_controller") -> None:
        """Select all geometry (brushes, curves, terrains)."""
        self.select_all_brushes(source=source)
        # TODO: select_all_curves(), select_all_terrains()

    def invert_selection(self, source: str = "edit_controller") -> None:
        """Invert current selection."""
        currently_selected = set(self.document.selection.selected_brushes)
        self.document.selection.clear(source=source)

        for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
            if (entity_idx, brush_idx) not in currently_selected:
                self.document.selection.select_brush(entity_idx, brush_idx, source=source)

    # =========================================================================
    # Delete
    # =========================================================================

    def delete_selected(self) -> int:
        """
        Delete all selected geometry.

        Returns:
            Total count of deleted items
        """
        deleted_count = 0

        # Delete brushes - get indices and remove in reverse order
        selected_indices = list(self.document.selection.selected_brushes)
        if selected_indices:
            # Clear selection first
            self.document.selection.clear_brushes(source="edit_controller")

            # Remove in reverse order to preserve indices
            for entity_idx, brush_idx in sorted(selected_indices, reverse=True):
                self.document.remove_brush(entity_idx, brush_idx)
                deleted_count += 1

            events.publish(BrushDeletedEvent(brush_ids=frozenset(selected_indices)))

        # TODO: Delete curves
        # TODO: Delete terrains

        return deleted_count

    # =========================================================================
    # Duplicate
    # =========================================================================

    def duplicate_selected(self, offset: tuple[float, float, float] | None = None) -> int:
        """
        Duplicate selected geometry with offset.

        Args:
            offset: Translation offset for duplicates. If None, uses grid size.

        Returns:
            Count of created duplicates
        """
        if offset is None:
            grid = self._window.get_grid_size()
            offset = (float(grid), float(grid), 0.0)

        offset_vec = Vec3(offset[0], offset[1], offset[2])
        created_count = 0

        # Duplicate brushes
        selected_brushes = self.document.selection.get_selected_brushes(self.document)
        if selected_brushes:
            self.document.selection.clear_brushes(source="edit_controller")

            for brush in selected_brushes:
                new_brush = brush.copy()
                new_brush.translate(offset_vec)

                result = self.document.add_brush_to_worldspawn(new_brush)
                if result:
                    entity_idx, brush_idx = result
                    self.document.selection.select_brush(entity_idx, brush_idx, source="edit_controller")
                    created_count += 1

        # TODO: Duplicate curves
        # TODO: Duplicate terrains

        return created_count

    # =========================================================================
    # Transform
    # =========================================================================

    def rotate_selected(self, axis: str, angle_degrees: float) -> None:
        """
        Rotate selected brushes around axis.

        Args:
            axis: 'x', 'y', or 'z'
            angle_degrees: Rotation angle in degrees
        """
        selected = self.document.selection.get_selected_brushes(self.document)
        if not selected:
            return

        # Calculate center of all selected brushes
        centers = []
        for brush in selected:
            c = get_brush_center(brush)
            centers.append(np.array([c.x, c.y, c.z]))
        rotation_center = np.mean(centers, axis=0)
        rotation_center_vec = Vec3(rotation_center[0], rotation_center[1], rotation_center[2])

        for brush in selected:
            brush.rotate(angle_degrees, axis, rotation_center_vec)

        events.publish(BrushGeometryModifiedEvent(
            brush_indices=self.document.selection.selected_brushes,
            modification_type="rotate"
        ))

    def scale_selected(self, factor: float) -> None:
        """
        Scale selected brushes.

        Args:
            factor: Scale factor (1.0 = no change)
        """
        selected = self.document.selection.get_selected_brushes(self.document)
        if not selected:
            return

        centers = []
        for brush in selected:
            c = get_brush_center(brush)
            centers.append(np.array([c.x, c.y, c.z]))
        scale_center = np.mean(centers, axis=0)
        scale_center_vec = Vec3(scale_center[0], scale_center[1], scale_center[2])

        for brush in selected:
            brush.scale(factor, scale_center_vec)

        events.publish(BrushGeometryModifiedEvent(
            brush_indices=self.document.selection.selected_brushes,
            modification_type="scale"
        ))

    def flip_selected(self, axis: str) -> None:
        """
        Flip/mirror selected brushes along axis.

        Args:
            axis: 'x', 'y', or 'z'
        """
        selected = self.document.selection.get_selected_brushes(self.document)
        if not selected:
            return

        centers = []
        for brush in selected:
            c = get_brush_center(brush)
            centers.append(np.array([c.x, c.y, c.z]))
        flip_center = np.mean(centers, axis=0)
        flip_center_vec = Vec3(flip_center[0], flip_center[1], flip_center[2])

        axis_idx = {'x': 0, 'y': 1, 'z': 2}.get(axis.lower(), 0)

        for brush in selected:
            brush.flip(axis_idx, flip_center_vec)

        events.publish(BrushGeometryModifiedEvent(
            brush_indices=self.document.selection.selected_brushes,
            modification_type="flip"
        ))
