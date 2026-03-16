"""Selection and picking handling for 3D viewport."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import moderngl

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QMouseEvent

from ...core import (
    Brush,
    Vec3,
    get_brush_center,
    get_brush_bounds,
    compute_brush_vertices,
    intersect_ray_brush,
)
from ...core import ui_state

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class SelectionHandler:
    """Handles brush and face selection, ray picking, and drag operations."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

        # Selected faces rendering
        self._selected_faces_vao: moderngl.VertexArray | None = None
        self._selected_faces_vbo: moderngl.Buffer | None = None
        self._selected_faces_vertex_count: int = 0

        # Drag state
        self._dragging = False
        self._drag_start_point: np.ndarray | None = None
        self._drag_plane_normal: np.ndarray | None = None
        self._drag_plane_distance: float = 0.0
        self._drag_start_positions: dict[int, np.ndarray] | None = None

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def brush_program(self) -> moderngl.Program | None:
        return self.viewport.brush_program

    @property
    def dragging(self) -> bool:
        return self._dragging

    def handle_selection_click(self, event: QMouseEvent):
        """Handle Shift+click for brush selection."""
        x = event.pos().x()
        y = event.pos().y()

        # Convert to ray
        ray_origin, ray_dir = self.viewport.camera.screen_to_ray(
            x, y, self.viewport.width(), self.viewport.height()
        )

        # Find closest intersecting brush using helper
        brush_key, closest_brush = self.get_brush_at_ray(ray_origin, ray_dir)

        # Handle selection - toggle on click
        if closest_brush is not None and brush_key is not None:
            entity_idx, brush_idx = brush_key
            self.viewport.document.selection.toggle_brush(entity_idx, brush_idx, source="viewport_3d")
            # Update this viewport since we ignore our own events
            batch_renderer = self.viewport._batch_renderer
            if batch_renderer is not None:
                batch_renderer.update_selection(
                    self.viewport.document.selection.selected_brushes
                )
            # Update face highlight (faces on this brush may have been deselected)
            self.rebuild_selected_faces_vao()
            self.viewport.update()

    def handle_face_selection_click(self, ray_origin: np.ndarray, ray_dir: np.ndarray):
        """Handle Ctrl+Shift+click for face selection."""
        closest_brush = None
        closest_brush_key: tuple[int, int] | None = None
        closest_face_idx = None
        closest_distance = float('inf')

        # Determine if filters are active
        filters = self.viewport._filters
        has_filters = bool(filters)
        visible_brushes = self.viewport._filtered_brushes if has_filters else None

        for entity_idx, brush_idx, brush in self.viewport.document.iter_all_geometry():
            brush_key = (entity_idx, brush_idx)

            # Use UIStateManager for visibility check
            if ui_state.is_brush_hidden(entity_idx, brush_idx):
                continue

            # Only regular brushes support face intersection, skip patches
            if not brush.is_regular:
                continue

            # Skip brushes that are filtered out (not visible)
            if visible_brushes is not None and brush_key not in visible_brushes:
                continue

            # Skip brushes that are already selected (face selection only on non-selected brushes)
            if brush_key in self.viewport.document.selection.selected_brushes:
                continue

            # Compute vertices for face intersection tests
            face_vertices = compute_brush_vertices(brush)

            # Test each face for intersection
            for face_idx, plane in enumerate(brush.planes):
                face_verts = face_vertices.get(face_idx, [])
                if len(face_verts) < 3:
                    continue

                # Check if ray intersects this face
                distance = self._ray_face_intersect_verts(ray_origin, ray_dir, face_verts, plane.normal)
                if distance is not None and distance < closest_distance:
                    closest_distance = distance
                    closest_brush = brush
                    closest_brush_key = brush_key
                    closest_face_idx = face_idx

        # Handle selection - toggle on click
        if closest_brush is not None and closest_brush_key is not None and closest_face_idx is not None:
            entity_idx, brush_idx = closest_brush_key

            # Toggle face selection
            if self.viewport.document.selection.is_face_selected(entity_idx, brush_idx, closest_face_idx):
                self.viewport.document.selection.deselect_face(entity_idx, brush_idx, closest_face_idx)
            else:
                # Add to existing selection (multi-face selection)
                self.viewport.document.selection.select_face(entity_idx, brush_idx, closest_face_idx, source="viewport_3d")

            # Rebuild face highlight geometry
            self.rebuild_selected_faces_vao()
            self.viewport.update()

    def get_brush_at_ray(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> tuple[tuple[int, int] | None, Brush | None]:
        """Find brush at ray using octree acceleration.

        Returns:
            Tuple of (brush_key, brush) or (None, None) if no hit
        """
        closest_brush = None
        closest_key: tuple[int, int] | None = None
        closest_distance = float('inf')

        # Determine if filters are active
        filters = self.viewport._filters
        has_filters = bool(filters)
        visible_brushes = self.viewport._filtered_brushes if has_filters else None

        # Convert ray to Vec3 for intersection test
        ray_origin_vec = Vec3(float(ray_origin[0]), float(ray_origin[1]), float(ray_origin[2]))
        ray_dir_vec = Vec3(float(ray_dir[0]), float(ray_dir[1]), float(ray_dir[2]))

        settings = self.viewport._settings_manager
        octree = self.viewport._octree

        if settings.octree_enabled and len(octree) > 0:
            # Use octree for accelerated picking
            candidate_keys = octree.query_ray(ray_origin, ray_dir)

            # Build a map of brush keys to brushes for fast lookup
            brush_map: dict[tuple[int, int], Brush] = {}
            for entity_idx, brush_idx, brush in self.viewport.document.iter_all_geometry():
                if brush.is_regular:
                    brush_map[(entity_idx, brush_idx)] = brush

            for brush_key in candidate_keys:
                if brush_key not in brush_map:
                    continue

                brush = brush_map[brush_key]
                # Use UIStateManager for visibility check
                if ui_state.is_brush_hidden(*brush_key):
                    continue

                # Skip brushes that are filtered out (not visible)
                if visible_brushes is not None and brush_key not in visible_brushes:
                    continue

                distance = intersect_ray_brush(brush, ray_origin_vec, ray_dir_vec)
                if distance is not None and distance < closest_distance:
                    closest_distance = distance
                    closest_brush = brush
                    closest_key = brush_key
        else:
            # Fallback: linear search
            for entity_idx, brush_idx, brush in self.viewport.document.iter_all_geometry():
                brush_key = (entity_idx, brush_idx)

                # Use UIStateManager for visibility check
                if ui_state.is_brush_hidden(entity_idx, brush_idx):
                    continue

                if not brush.is_regular:
                    continue

                # Skip brushes that are filtered out (not visible)
                if visible_brushes is not None and brush_key not in visible_brushes:
                    continue

                distance = intersect_ray_brush(brush, ray_origin_vec, ray_dir_vec)
                if distance is not None and distance < closest_distance:
                    closest_distance = distance
                    closest_brush = brush
                    closest_key = brush_key

        return closest_key, closest_brush

    def ray_plane_intersect(self, ray_origin: np.ndarray, ray_dir: np.ndarray,
                            plane_normal: np.ndarray, plane_distance: float) -> np.ndarray | None:
        """Intersect ray with plane, return intersection point."""
        denom = np.dot(ray_dir, plane_normal)
        if abs(denom) < 1e-6:
            return None  # Ray parallel to plane

        t = (plane_distance - np.dot(ray_origin, plane_normal)) / denom
        if t < 0:
            return None  # Behind camera

        return ray_origin + ray_dir * t

    def _ray_face_intersect_verts(self, ray_origin: np.ndarray, ray_dir: np.ndarray, vertices: list, normal) -> float | None:
        """Test ray intersection with a face polygon.

        Returns distance to intersection or None if no intersection.
        """
        if len(vertices) < 3:
            return None

        # Convert normal to numpy if it's a Vec3
        if hasattr(normal, 'x'):
            normal_np = np.array([normal.x, normal.y, normal.z])
        else:
            normal_np = normal

        # Validate normal
        if np.isnan(normal_np).any():
            return None

        # Check ray-plane intersection
        denom = np.dot(ray_dir, normal_np)
        if abs(denom) < 1e-6:
            return None  # Ray parallel to face

        # Get first vertex for plane distance calculation
        v0 = vertices[0]
        if hasattr(v0, 'x'):
            v0_np = np.array([v0.x, v0.y, v0.z])
        else:
            v0_np = np.asarray(v0)

        # Distance from origin to plane along normal
        d = np.dot(v0_np, normal_np)
        t = (d - np.dot(ray_origin, normal_np)) / denom

        if t < 0:
            return None  # Behind camera

        # Get intersection point
        hit_point = ray_origin + ray_dir * t

        # Convert vertices to numpy for point-in-polygon test
        vertices_np = []
        for v in vertices:
            if hasattr(v, 'x'):
                vertices_np.append(np.array([v.x, v.y, v.z]))
            else:
                vertices_np.append(np.asarray(v))

        # Check if point is inside the polygon using ray casting algorithm
        if self._point_in_polygon(hit_point, vertices_np, normal_np):
            return t

        return None

    def _point_in_polygon(self, point: np.ndarray, vertices: list, normal: np.ndarray) -> bool:
        """Check if a point lies inside a polygon using 2D projection."""
        n = len(vertices)
        if n < 3:
            return False

        # Find the dominant axis (largest component of normal)
        abs_normal = np.abs(normal)
        dominant_axis = np.argmax(abs_normal)

        # Choose projection axes (drop the dominant axis)
        if dominant_axis == 0:  # X is dominant, project to YZ
            axis1, axis2 = 1, 2
        elif dominant_axis == 1:  # Y is dominant, project to XZ
            axis1, axis2 = 0, 2
        else:  # Z is dominant, project to XY
            axis1, axis2 = 0, 1

        # Project point and vertices to 2D
        px, py = point[axis1], point[axis2]

        # Ray casting algorithm - count intersections
        inside = False
        j = n - 1

        for i in range(n):
            vi = vertices[i]
            vj = vertices[j]

            xi, yi = vi[axis1], vi[axis2]
            xj, yj = vj[axis1], vj[axis2]

            # Check if ray from (px, py) going right intersects edge (vi, vj)
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside

            j = i

        return inside

    # =========================================================================
    # Drag Operations
    # =========================================================================

    def start_drag_3d(self, clicked_brush: Brush, brush_key: tuple[int, int], ray_origin: np.ndarray, ray_dir: np.ndarray):
        """Start dragging selected brushes in 3D."""
        # Use a plane through the clicked brush center, facing the camera
        center = get_brush_center(clicked_brush)
        brush_center = np.array([center.x, center.y, center.z], dtype=np.float64)

        # Plane normal is the camera's forward direction (facing camera)
        self._drag_plane_normal = -self.viewport.camera.forward.astype(np.float64)
        self._drag_plane_distance = float(np.dot(brush_center, self._drag_plane_normal))

        # Find the intersection point on this plane
        self._drag_start_point = self.ray_plane_intersect(
            ray_origin, ray_dir, self._drag_plane_normal, self._drag_plane_distance
        )

        if self._drag_start_point is None:
            return

        self._dragging = True
        self._drag_start_positions = {}

        # Store original positions of all selected brushes
        for brush in self.viewport.document.selection.get_selected_brushes(self.viewport.document):
            center = get_brush_center(brush)
            self._drag_start_positions[brush.index] = np.array([center.x, center.y, center.z], dtype=np.float64)

        self.viewport.setCursor(Qt.CursorShape.SizeAllCursor)

    def update_drag_3d(self, ray_origin: np.ndarray, ray_dir: np.ndarray):
        """Update brush positions during 3D drag."""
        if not self._dragging or self._drag_start_point is None:
            return

        # Find current intersection with drag plane
        current_point = self.ray_plane_intersect(
            ray_origin, ray_dir, self._drag_plane_normal, self._drag_plane_distance
        )

        if current_point is None:
            return

        # Calculate delta
        delta = current_point - self._drag_start_point

        # Snap to grid
        grid_size = self.viewport.grid_size
        delta[0] = round(delta[0] / grid_size) * grid_size
        delta[1] = round(delta[1] / grid_size) * grid_size
        delta[2] = round(delta[2] / grid_size) * grid_size

        # Move all selected brushes
        for brush in self.viewport.document.selection.get_selected_brushes(self.viewport.document):
            if brush.index in self._drag_start_positions:
                original_center = self._drag_start_positions[brush.index]
                center = get_brush_center(brush)
                current_center = np.array([center.x, center.y, center.z])

                target_center = original_center + delta
                move_offset = target_center - current_center

                brush.translate(Vec3(move_offset[0], move_offset[1], move_offset[2]))

        # Update viewports
        self.viewport.update()
        self._notify_2d_viewport()

    def end_drag_3d(self):
        """End 3D dragging."""
        self._dragging = False
        self._drag_start_point = None
        self._drag_plane_normal = None
        self._drag_start_positions = None
        # Rebuild geometry after drag completes
        self.viewport._geometry_builder.rebuild_moved_brushes()
        # Notify that geometry changed
        self.viewport.geometry_changed.emit()

    def _notify_2d_viewport(self):
        """Notify 2D viewport to update."""
        parent = self.viewport.parent()
        while parent:
            if hasattr(parent, 'viewport_2d'):
                parent.viewport_2d.update()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    # =========================================================================
    # Face Highlight VAO
    # =========================================================================

    def rebuild_selected_faces_vao(self):
        """Rebuild the VAO for selected face highlighting."""
        if self.ctx is None or self.brush_program is None:
            return

        # Make context current for OpenGL operations
        self.viewport.makeCurrent()
        try:
            # Release old VAO/VBO
            if self._selected_faces_vao is not None:
                self._selected_faces_vao.release()
                self._selected_faces_vao = None
            if self._selected_faces_vbo is not None:
                self._selected_faces_vbo.release()
                self._selected_faces_vbo = None
            self._selected_faces_vertex_count = 0

            # Get selected faces (returns set of (entity_idx, brush_idx, face_idx))
            selected_faces = self.viewport.document.selection.get_selected_faces()
            if not selected_faces:
                return

            vertices = []

            for entity_idx, brush_idx, face_idx in selected_faces:
                brush = self.viewport.document.get_brush(entity_idx, brush_idx)
                if brush is None:
                    print(f"[Face Highlight] Brush ({entity_idx}, {brush_idx}) not found")
                    continue
                if face_idx >= len(brush.planes):
                    print(f"[Face Highlight] Face index {face_idx} out of range for brush ({entity_idx}, {brush_idx})")
                    continue

                # Compute vertices for this face
                face_vertices = compute_brush_vertices(brush)
                face_verts = face_vertices.get(face_idx, [])
                if len(face_verts) < 3:
                    print(f"[Face Highlight] Face {face_idx} has < 3 vertices")
                    continue

                plane = brush.planes[face_idx]
                normal = plane.normal
                if math.isnan(normal.x) or math.isnan(normal.y) or math.isnan(normal.z):
                    print(f"[Face Highlight] Face {face_idx} has invalid normal")
                    continue

                # Offset vertices slightly along normal to avoid z-fighting
                offset_x = normal.x * 0.5
                offset_y = normal.y * 0.5
                offset_z = normal.z * 0.5

                # Triangulate the face (fan triangulation)
                for i in range(1, len(face_verts) - 1):
                    v0 = face_verts[0]
                    v1 = face_verts[i]
                    v2 = face_verts[i + 1]

                    # Add vertices with offset, normal and dummy texcoord
                    for v in [v0, v1, v2]:
                        vertices.extend([
                            float(v.x + offset_x), float(v.y + offset_y), float(v.z + offset_z),
                            float(normal.x), float(normal.y), float(normal.z),
                            0.0, 0.0  # Placeholder texcoords
                        ])

            if not vertices:
                print(f"[Face Highlight] No vertices generated for {len(selected_faces)} selected faces")
                return

            vertices_array = np.array(vertices, dtype='f4')
            self._selected_faces_vbo = self.ctx.buffer(vertices_array.tobytes())
            self._selected_faces_vao = self.ctx.vertex_array(
                self.brush_program,
                [(self._selected_faces_vbo, '3f 3f 2f', 'in_position', 'in_normal', 'in_texcoord')]
            )
            self._selected_faces_vertex_count = len(vertices) // 8  # 8 floats per vertex
            print(f"[Face Highlight] Created VAO with {self._selected_faces_vertex_count} vertices for {len(selected_faces)} faces")
        finally:
            self.viewport.doneCurrent()

    @property
    def selected_faces_vao(self) -> moderngl.VertexArray | None:
        return self._selected_faces_vao

    @property
    def selected_faces_vertex_count(self) -> int:
        return self._selected_faces_vertex_count
