"""Brush operations controller - Creation, CSG operations."""

from __future__ import annotations
from typing import TYPE_CHECKING
import numpy as np

from ...core import (
    events,
    BrushCreatedEvent,
    BrushGeometryModifiedEvent,
    Brush,
    BrushPlane,
    Vec3,
    create_block,
    create_cylinder,
    create_cone,
    create_wedge,
    create_spike,
    get_all_brush_vertices,
)

if TYPE_CHECKING:
    from ..main_window import MainWindow
    from ...core import MapDocument


class BrushController:
    """
    Handles brush-specific operations.

    Responsibilities:
    - Primitive creation (block, cylinder, cone, sphere, wedge)
    - CSG operations (hollow, clip)
    - Brush-specific tools
    """

    def __init__(self, main_window: "MainWindow") -> None:
        self._window = main_window

    @property
    def document(self) -> "MapDocument":
        return self._window.document

    # =========================================================================
    # Primitive Creation
    # =========================================================================

    def create_block_brush(
        self,
        min_point: tuple[float, float, float],
        max_point: tuple[float, float, float],
        texture: str = "common/caulk"
    ) -> Brush | None:
        """
        Create a block brush.

        Args:
            min_point: Minimum corner (x, y, z)
            max_point: Maximum corner (x, y, z)
            texture: Texture name for all faces

        Returns:
            Created Brush or None on failure
        """
        min_v = Vec3(min_point[0], min_point[1], min_point[2])
        max_v = Vec3(max_point[0], max_point[1], max_point[2])

        # Validate
        if max_v.x <= min_v.x or max_v.y <= min_v.y or max_v.z <= min_v.z:
            return None

        brush = create_block(min_v, max_v, texture)
        if brush is None:
            return None

        result = self.document.add_brush_to_worldspawn(brush)
        if result is None:
            return None

        entity_idx, brush_idx = result

        events.publish(BrushCreatedEvent(
            brush_index=(entity_idx, brush_idx),
            entity_index=entity_idx
        ))

        return brush

    # =========================================================================
    # CSG Operations
    # =========================================================================

    def hollow_selected(self, wall_thickness: float) -> int:
        """
        Hollow selected brushes.

        Args:
            wall_thickness: Thickness of walls

        Returns:
            Number of brushes created
        """
        selected_indices = list(self.document.selection.selected_brushes)
        if not selected_indices:
            return 0

        created = 0

        # Remove brushes in reverse order
        for entity_idx, brush_idx in sorted(selected_indices, reverse=True):
            brush = self.document.get_brush(entity_idx, brush_idx)
            if brush is None:
                continue

            new_brushes = self._hollow_brush(brush, wall_thickness)
            if new_brushes:
                # Remove original
                self.document.remove_brush(entity_idx, brush_idx)

                # Add hollowed walls
                for new_brush in new_brushes:
                    self.document.add_brush_to_worldspawn(new_brush)
                    created += 1

        return created

    def _hollow_brush(self, brush: Brush, thickness: float) -> list[Brush]:
        """Internal: Create hollow version of brush."""
        # TODO: Implement proper CSG hollowing
        # For now, return empty list
        return []

    # =========================================================================
    # Texture Operations
    # =========================================================================

    def set_texture_on_selected(self, texture: str) -> int:
        """
        Set texture on all selected brush faces.

        Args:
            texture: Texture path

        Returns:
            Number of faces modified
        """
        selected = self.document.selection.get_selected_brushes(self.document)
        modified = 0

        for brush in selected:
            for plane in brush.planes:
                plane.shader = texture
                modified += 1

        if modified > 0:
            events.publish(BrushGeometryModifiedEvent(
                brush_indices=self.document.selection.selected_brushes,
                modification_type="texture"
            ))

        return modified

    # =========================================================================
    # Generic Primitive Creation
    # =========================================================================

    def create_primitive_at_viewport_center(
        self,
        primitive_type: str,
        texture: str = "common/caulk"
    ) -> Brush | None:
        """
        Create a primitive at the current 2D viewport center.

        Args:
            primitive_type: Type of primitive ("block", "cylinder", "cone", "wedge", "spike")
            texture: Texture name for all faces

        Returns:
            Created Brush or None on failure
        """
        viewport_2d = self._window.viewport_2d
        if viewport_2d is None:
            return None

        # Get grid size for dimensions
        grid = viewport_2d.grid_size
        size = grid * 4  # 4 grid units as default size

        # Get center position from 2D viewport
        center_x = viewport_2d.offset_x
        center_y = viewport_2d.offset_y

        # Snap to grid
        center_x = round(center_x / grid) * grid
        center_y = round(center_y / grid) * grid

        # Map 2D coordinates to 3D based on current view axis
        axis = viewport_2d.axis
        if axis == 'xy':
            center = Vec3(center_x, center_y, 0)
        elif axis == 'xz':
            center = Vec3(center_x, 0, center_y)
        else:  # yz
            center = Vec3(0, center_x, center_y)

        if primitive_type == "block":
            min_pt = Vec3(center.x - size/2, center.y - size/2, center.z)
            max_pt = Vec3(center.x + size/2, center.y + size/2, center.z + size)
            brush = create_block(min_pt, max_pt, texture)
        elif primitive_type == "cylinder":
            brush = create_cylinder(center, radius=size/2, height=size, sides=8, shader=texture)
        elif primitive_type == "cone":
            brush = create_cone(center, radius=size/2, height=size, sides=8, shader=texture)
        elif primitive_type == "wedge":
            min_pt = Vec3(center.x - size/2, center.y - size/2, center.z)
            max_pt = Vec3(center.x + size/2, center.y + size/2, center.z + size)
            brush = create_wedge(min_pt, max_pt, texture)
        elif primitive_type == "spike":
            brush = create_spike(center, base_size=size/2, height=size, shader=texture)
        else:
            return None

        if brush is None:
            return None

        # Add brush to document
        result = self.document.add_brush_to_worldspawn(brush)
        if result is None:
            return None

        entity_idx, brush_idx = result

        # Clear selection and select new brush
        self.document.selection.clear_brushes(source="brush_controller")
        self.document.selection.select_brush(entity_idx, brush_idx, source="brush_controller")

        events.publish(BrushCreatedEvent(
            brush_index=(entity_idx, brush_idx),
            entity_index=entity_idx
        ))

        return brush

    # =========================================================================
    # Utilities
    # =========================================================================

    def get_selection_bounds(self) -> tuple[np.ndarray, np.ndarray] | None:
        """
        Get bounding box of selected brushes.

        Returns:
            Tuple of (min_point, max_point) or None if no selection
        """
        selected = self.document.selection.get_selected_brushes(self.document)
        if not selected:
            return None

        all_vertices = []
        for brush in selected:
            verts = get_all_brush_vertices(brush)
            for v in verts:
                all_vertices.append([v.x, v.y, v.z])

        if not all_vertices:
            return None

        vertices = np.array(all_vertices)
        min_point = vertices.min(axis=0)
        max_point = vertices.max(axis=0)

        return min_point, max_point
