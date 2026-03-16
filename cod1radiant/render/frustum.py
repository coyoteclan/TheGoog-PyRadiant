"""View frustum for culling objects outside the camera's field of view."""

from __future__ import annotations

import numpy as np
from enum import IntEnum


class FrustumPlane(IntEnum):
    """Indices for frustum planes."""
    LEFT = 0
    RIGHT = 1
    BOTTOM = 2
    TOP = 3
    NEAR = 4
    FAR = 5


class Frustum:
    """
    View frustum for efficient culling of objects outside the camera view.

    Extracts 6 clip planes from the view-projection matrix and provides
    fast AABB intersection tests.
    """

    __slots__ = ('planes', '_planes_array')

    def __init__(self):
        # Each plane: (nx, ny, nz, d) where nx*x + ny*y + nz*z + d = 0
        # Stored as 6x4 array for vectorized operations
        self.planes = np.zeros((6, 4), dtype=np.float32)
        self._planes_array = self.planes  # Alias for direct access

    def update_from_matrix(self, mvp: np.ndarray):
        """
        Extract frustum planes from a Model-View-Projection matrix.

        Uses the Gribb/Hartmann method for plane extraction.
        The matrix should be in row-major format (as used in this project).

        Args:
            mvp: 4x4 MVP matrix (row-major, not transposed)
        """
        # Ensure we're working with the right format
        m = np.asarray(mvp, dtype=np.float32)

        # Extract planes using Gribb/Hartmann method
        # For row-major matrices:
        # Left:   row3 + row0
        # Right:  row3 - row0
        # Bottom: row3 + row1
        # Top:    row3 - row1
        # Near:   row3 + row2
        # Far:    row3 - row2

        # Left plane
        self.planes[FrustumPlane.LEFT] = m[3] + m[0]
        # Right plane
        self.planes[FrustumPlane.RIGHT] = m[3] - m[0]
        # Bottom plane
        self.planes[FrustumPlane.BOTTOM] = m[3] + m[1]
        # Top plane
        self.planes[FrustumPlane.TOP] = m[3] - m[1]
        # Near plane
        self.planes[FrustumPlane.NEAR] = m[3] + m[2]
        # Far plane
        self.planes[FrustumPlane.FAR] = m[3] - m[2]

        # Normalize all planes
        self._normalize_planes()

    def _normalize_planes(self):
        """Normalize all frustum planes."""
        for i in range(6):
            normal_length = np.linalg.norm(self.planes[i, :3])
            if normal_length > 1e-6:
                self.planes[i] /= normal_length

    def test_aabb(self, aabb_min: np.ndarray, aabb_max: np.ndarray) -> bool:
        """
        Test if an AABB intersects or is inside the frustum.

        Uses the "p-vertex" optimization: for each plane, find the corner
        of the AABB that is most in the direction of the plane normal.
        If this corner is outside, the entire AABB is outside.

        Args:
            aabb_min: Minimum corner of the AABB (x, y, z)
            aabb_max: Maximum corner of the AABB (x, y, z)

        Returns:
            True if AABB is potentially visible (intersects or inside frustum)
            False if AABB is completely outside frustum
        """
        for i in range(6):
            plane = self.planes[i]
            nx, ny, nz, d = plane[0], plane[1], plane[2], plane[3]

            # Find the p-vertex (most positive vertex relative to plane normal)
            px = aabb_max[0] if nx >= 0 else aabb_min[0]
            py = aabb_max[1] if ny >= 0 else aabb_min[1]
            pz = aabb_max[2] if nz >= 0 else aabb_min[2]

            # If p-vertex is outside this plane, AABB is completely outside
            if nx * px + ny * py + nz * pz + d < 0:
                return False

        return True

    def test_aabb_fast(self, aabb_min: np.ndarray, aabb_max: np.ndarray) -> bool:
        """
        Faster AABB test using NumPy vectorization.

        Same logic as test_aabb but optimized for batch processing.
        """
        # Build p-vertices for all 6 planes at once
        # Shape: (6, 3) - one p-vertex per plane
        normals = self.planes[:, :3]  # (6, 3)

        # For each component, select max if normal >= 0, else min
        p_vertices = np.where(
            normals >= 0,
            aabb_max,  # broadcasts to (6, 3)
            aabb_min   # broadcasts to (6, 3)
        )

        # Compute signed distances: dot(normal, p_vertex) + d
        # dot product per row: sum of element-wise multiplication
        distances = np.sum(normals * p_vertices, axis=1) + self.planes[:, 3]

        # AABB is outside if any p-vertex is outside its plane
        return not np.any(distances < 0)

    def test_aabbs_batch(
        self,
        aabb_mins: np.ndarray,
        aabb_maxs: np.ndarray
    ) -> np.ndarray:
        """
        Test multiple AABBs against the frustum in a single vectorized operation.

        Args:
            aabb_mins: Array of shape (N, 3) with minimum corners
            aabb_maxs: Array of shape (N, 3) with maximum corners

        Returns:
            Boolean array of shape (N,) - True if AABB is visible
        """
        n_boxes = aabb_mins.shape[0]

        # For each plane and each box, compute p-vertex and test
        # planes: (6, 4), mins/maxs: (N, 3)

        normals = self.planes[:, :3]  # (6, 3)
        d_values = self.planes[:, 3]  # (6,)

        # Result array - start assuming all visible
        visible = np.ones(n_boxes, dtype=bool)

        for plane_idx in range(6):
            nx, ny, nz = normals[plane_idx]
            d = d_values[plane_idx]

            # Select p-vertex components for all boxes
            px = np.where(nx >= 0, aabb_maxs[:, 0], aabb_mins[:, 0])
            py = np.where(ny >= 0, aabb_maxs[:, 1], aabb_mins[:, 1])
            pz = np.where(nz >= 0, aabb_maxs[:, 2], aabb_mins[:, 2])

            # Compute distances
            distances = nx * px + ny * py + nz * pz + d

            # Mark boxes outside this plane as not visible
            visible &= (distances >= 0)

        return visible

    def test_sphere(self, center: np.ndarray, radius: float) -> bool:
        """
        Test if a bounding sphere intersects or is inside the frustum.

        Args:
            center: Center of the sphere (x, y, z)
            radius: Radius of the sphere

        Returns:
            True if sphere is potentially visible
        """
        for i in range(6):
            plane = self.planes[i]
            # Signed distance from center to plane
            distance = (
                plane[0] * center[0] +
                plane[1] * center[1] +
                plane[2] * center[2] +
                plane[3]
            )
            # If center is more than radius outside, sphere is invisible
            if distance < -radius:
                return False

        return True

    def test_point(self, point: np.ndarray) -> bool:
        """
        Test if a point is inside the frustum.

        Args:
            point: 3D point (x, y, z)

        Returns:
            True if point is inside frustum
        """
        for i in range(6):
            plane = self.planes[i]
            distance = (
                plane[0] * point[0] +
                plane[1] * point[1] +
                plane[2] * point[2] +
                plane[3]
            )
            if distance < 0:
                return False

        return True


class FrustumCuller:
    """
    Helper class for culling brushes with cached bounds.

    Maintains a cache of brush AABBs and provides efficient batch culling.
    Keys are (entity_idx, brush_idx) tuples.
    """

    __slots__ = ('frustum', '_bounds_cache', '_bounds_arrays')

    def __init__(self):
        self.frustum = Frustum()
        # Cache: brush_key -> (min, max)
        self._bounds_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        # Flattened arrays for batch processing
        self._bounds_arrays: tuple[np.ndarray, np.ndarray] | None = None

    def update_frustum(self, mvp: np.ndarray):
        """Update the frustum from the current MVP matrix."""
        self.frustum.update_from_matrix(mvp)

    def set_brush_bounds(self, brush_key: tuple[int, int], aabb_min, aabb_max):
        """Update cached bounds for a brush.

        Args:
            brush_key: (entity_idx, brush_idx) tuple
            aabb_min: Minimum point (can be Vec3 or array)
            aabb_max: Maximum point (can be Vec3 or array)
        """
        # Handle Vec3 input
        if hasattr(aabb_min, 'x'):
            aabb_min = np.array([aabb_min.x, aabb_min.y, aabb_min.z], dtype=np.float32)
        if hasattr(aabb_max, 'x'):
            aabb_max = np.array([aabb_max.x, aabb_max.y, aabb_max.z], dtype=np.float32)

        self._bounds_cache[brush_key] = (
            np.asarray(aabb_min, dtype=np.float32),
            np.asarray(aabb_max, dtype=np.float32)
        )
        self._bounds_arrays = None  # Invalidate batch arrays

    def remove_brush(self, brush_key: tuple[int, int]):
        """Remove a brush from the cache."""
        if brush_key in self._bounds_cache:
            del self._bounds_cache[brush_key]
            self._bounds_arrays = None

    def clear(self):
        """Clear all cached bounds."""
        self._bounds_cache.clear()
        self._bounds_arrays = None

    def is_visible(self, brush_key: tuple[int, int]) -> bool:
        """Test if a single brush is visible."""
        if brush_key not in self._bounds_cache:
            return True  # Assume visible if no bounds cached

        aabb_min, aabb_max = self._bounds_cache[brush_key]
        return self.frustum.test_aabb(aabb_min, aabb_max)

    def get_visible_brush_keys(self) -> set[tuple[int, int]]:
        """
        Get all brush keys that are currently visible.

        Uses batch processing for efficiency.
        """
        if not self._bounds_cache:
            return set()

        brush_keys = list(self._bounds_cache.keys())
        n = len(brush_keys)

        # Build arrays if not cached
        if self._bounds_arrays is None:
            mins = np.zeros((n, 3), dtype=np.float32)
            maxs = np.zeros((n, 3), dtype=np.float32)
            for i, bkey in enumerate(brush_keys):
                mins[i], maxs[i] = self._bounds_cache[bkey]
            self._bounds_arrays = (mins, maxs)

        mins, maxs = self._bounds_arrays

        # Batch test
        visible_mask = self.frustum.test_aabbs_batch(mins, maxs)

        # Return visible keys
        return {brush_keys[i] for i in range(n) if visible_mask[i]}

    def get_culling_stats(self) -> tuple[int, int]:
        """
        Get culling statistics.

        Returns:
            Tuple of (visible_count, total_count)
        """
        if not self._bounds_cache:
            return (0, 0)

        visible = self.get_visible_brush_keys()
        return (len(visible), len(self._bounds_cache))
