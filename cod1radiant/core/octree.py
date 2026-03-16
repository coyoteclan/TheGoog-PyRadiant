"""Octree spatial data structure for efficient ray-casting and spatial queries."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterator
import numpy as np

if TYPE_CHECKING:
    from . import Brush


@dataclass
class AABB:
    """Axis-Aligned Bounding Box."""
    min_point: np.ndarray
    max_point: np.ndarray

    def __post_init__(self):
        self.min_point = np.asarray(self.min_point, dtype=np.float64)
        self.max_point = np.asarray(self.max_point, dtype=np.float64)

    @property
    def center(self) -> np.ndarray:
        return (self.min_point + self.max_point) * 0.5

    @property
    def size(self) -> np.ndarray:
        return self.max_point - self.min_point

    @property
    def half_size(self) -> np.ndarray:
        return self.size * 0.5

    def contains_point(self, point: np.ndarray) -> bool:
        """Check if a point is inside the AABB."""
        return np.all(point >= self.min_point) and np.all(point <= self.max_point)

    def intersects(self, other: "AABB") -> bool:
        """Check if this AABB intersects another AABB."""
        return (
            np.all(self.min_point <= other.max_point) and
            np.all(self.max_point >= other.min_point)
        )

    def contains_aabb(self, other: "AABB") -> bool:
        """Check if this AABB fully contains another AABB."""
        return (
            np.all(self.min_point <= other.min_point) and
            np.all(self.max_point >= other.max_point)
        )

    def expand_to_contain(self, other: "AABB") -> "AABB":
        """Return a new AABB that contains both this and other."""
        return AABB(
            np.minimum(self.min_point, other.min_point),
            np.maximum(self.max_point, other.max_point)
        )

    def intersect_ray(self, ray_origin: np.ndarray, ray_dir: np.ndarray) -> tuple[bool, float, float]:
        """
        Test ray-AABB intersection using the slab method.

        Args:
            ray_origin: Ray starting point
            ray_dir: Normalized ray direction

        Returns:
            Tuple of (hit, t_min, t_max) where t values are ray parameters
        """
        t_min = 0.0
        t_max = float('inf')

        for i in range(3):
            if abs(ray_dir[i]) < 1e-10:
                # Ray parallel to slab
                if ray_origin[i] < self.min_point[i] or ray_origin[i] > self.max_point[i]:
                    return False, 0.0, 0.0
            else:
                inv_d = 1.0 / ray_dir[i]
                t1 = (self.min_point[i] - ray_origin[i]) * inv_d
                t2 = (self.max_point[i] - ray_origin[i]) * inv_d

                if t1 > t2:
                    t1, t2 = t2, t1

                t_min = max(t_min, t1)
                t_max = min(t_max, t2)

                if t_min > t_max:
                    return False, 0.0, 0.0

        return True, t_min, t_max


@dataclass(eq=False)
class OctreeNode:
    """A node in the octree (uses object identity for hashing)."""
    bounds: AABB
    depth: int = 0
    children: list["OctreeNode"] | None = None
    brush_keys: set[tuple[int, int]] = field(default_factory=set)  # (entity_idx, brush_idx)

    # Constants
    MAX_DEPTH: int = 8
    MAX_ITEMS_PER_NODE: int = 8

    def is_leaf(self) -> bool:
        return self.children is None

    def subdivide(self):
        """Split this node into 8 children."""
        if self.children is not None:
            return

        center = self.bounds.center
        min_p = self.bounds.min_point
        max_p = self.bounds.max_point

        self.children = []

        # Create 8 child nodes for each octant
        for i in range(8):
            # Bit pattern: i = zyx (z is bit 2, y is bit 1, x is bit 0)
            child_min = np.array([
                center[0] if (i & 1) else min_p[0],
                center[1] if (i & 2) else min_p[1],
                center[2] if (i & 4) else min_p[2]
            ])
            child_max = np.array([
                max_p[0] if (i & 1) else center[0],
                max_p[1] if (i & 2) else center[1],
                max_p[2] if (i & 4) else center[2]
            ])

            self.children.append(OctreeNode(
                bounds=AABB(child_min, child_max),
                depth=self.depth + 1
            ))

    def get_child_index(self, point: np.ndarray) -> int:
        """Get the index of the child that contains a point."""
        center = self.bounds.center
        index = 0
        if point[0] >= center[0]:
            index |= 1
        if point[1] >= center[1]:
            index |= 2
        if point[2] >= center[2]:
            index |= 4
        return index

    def get_intersecting_children(self, aabb: AABB) -> list[int]:
        """Get indices of children that intersect with an AABB."""
        if self.children is None:
            return []

        indices = []
        for i, child in enumerate(self.children):
            if child.bounds.intersects(aabb):
                indices.append(i)
        return indices


class BrushOctree:
    """
    Octree for efficient spatial queries on brushes.

    Provides O(log n) performance for:
    - Ray casting (picking)
    - Frustum culling
    - Collision detection

    Uses (entity_idx, brush_idx) tuples as brush keys.
    """

    def __init__(self, world_bounds: AABB | None = None):
        """
        Initialize the octree.

        Args:
            world_bounds: Initial world bounds. If None, uses a large default.
        """
        if world_bounds is None:
            # Default to a large world (matching typical Radiant map bounds)
            world_bounds = AABB(
                np.array([-16384, -16384, -16384], dtype=np.float64),
                np.array([16384, 16384, 16384], dtype=np.float64)
            )

        self.root = OctreeNode(bounds=world_bounds, depth=0)
        self._brush_bounds: dict[tuple[int, int], AABB] = {}
        self._brush_nodes: dict[tuple[int, int], set[OctreeNode]] = {}
        self._count = 0

    def clear(self):
        """Remove all brushes from the octree."""
        self.root = OctreeNode(bounds=self.root.bounds, depth=0)
        self._brush_bounds.clear()
        self._brush_nodes.clear()
        self._count = 0

    def insert(self, brush_key: tuple[int, int], aabb_min, aabb_max):
        """
        Insert a brush into the octree.

        Args:
            brush_key: (entity_idx, brush_idx) tuple
            aabb_min: Minimum corner of brush AABB (can be Vec3 or array)
            aabb_max: Maximum corner of brush AABB (can be Vec3 or array)
        """
        # Handle Vec3 input
        if hasattr(aabb_min, 'x'):
            aabb_min = np.array([aabb_min.x, aabb_min.y, aabb_min.z], dtype=np.float64)
        if hasattr(aabb_max, 'x'):
            aabb_max = np.array([aabb_max.x, aabb_max.y, aabb_max.z], dtype=np.float64)

        aabb = AABB(aabb_min, aabb_max)
        self._brush_bounds[brush_key] = aabb
        self._brush_nodes[brush_key] = set()

        self._insert_recursive(self.root, brush_key, aabb)
        self._count += 1

    def _insert_recursive(self, node: OctreeNode, brush_key: tuple[int, int], aabb: AABB):
        """Recursively insert a brush into the tree."""
        # If the brush doesn't intersect this node, skip
        if not node.bounds.intersects(aabb):
            return

        # If leaf node
        if node.is_leaf():
            # Add to this node
            node.brush_keys.add(brush_key)
            self._brush_nodes[brush_key].add(node)

            # Check if we need to subdivide
            if (len(node.brush_keys) > OctreeNode.MAX_ITEMS_PER_NODE and
                    node.depth < OctreeNode.MAX_DEPTH):
                self._subdivide_and_redistribute(node)
        else:
            # Insert into intersecting children
            for i in node.get_intersecting_children(aabb):
                self._insert_recursive(node.children[i], brush_key, aabb)

    def _subdivide_and_redistribute(self, node: OctreeNode):
        """Subdivide a node and redistribute its brushes to children."""
        node.subdivide()

        # Redistribute brushes to children
        brushes_to_redistribute = list(node.brush_keys)
        node.brush_keys.clear()

        for brush_key in brushes_to_redistribute:
            if brush_key in self._brush_bounds:
                aabb = self._brush_bounds[brush_key]
                self._brush_nodes[brush_key].discard(node)

                for i in node.get_intersecting_children(aabb):
                    self._insert_recursive(node.children[i], brush_key, aabb)

    def remove(self, brush_key: tuple[int, int]):
        """Remove a brush from the octree."""
        if brush_key not in self._brush_nodes:
            return

        # Remove from all nodes containing this brush
        for node in self._brush_nodes[brush_key]:
            node.brush_keys.discard(brush_key)

        del self._brush_nodes[brush_key]
        if brush_key in self._brush_bounds:
            del self._brush_bounds[brush_key]

        self._count -= 1

    def update(self, brush_key: tuple[int, int], aabb_min, aabb_max):
        """
        Update a brush's position in the octree.

        This is a remove + insert operation.
        """
        self.remove(brush_key)
        self.insert(brush_key, aabb_min, aabb_max)

    def query_ray(
        self,
        ray_origin: np.ndarray,
        ray_dir: np.ndarray,
        max_distance: float = float('inf')
    ) -> list[tuple[int, int]]:
        """
        Query brushes that potentially intersect a ray.

        This returns brush keys whose AABBs intersect the ray.
        You still need to do precise brush intersection tests.

        Args:
            ray_origin: Ray starting point
            ray_dir: Normalized ray direction
            max_distance: Maximum ray distance

        Returns:
            List of brush keys (entity_idx, brush_idx) that potentially intersect the ray
        """
        ray_origin = np.asarray(ray_origin, dtype=np.float64)
        ray_dir = np.asarray(ray_dir, dtype=np.float64)

        # Normalize direction
        dir_len = np.linalg.norm(ray_dir)
        if dir_len < 1e-10:
            return []
        ray_dir = ray_dir / dir_len

        results: set[tuple[int, int]] = set()
        self._query_ray_recursive(self.root, ray_origin, ray_dir, max_distance, results)
        return list(results)

    def _query_ray_recursive(
        self,
        node: OctreeNode,
        ray_origin: np.ndarray,
        ray_dir: np.ndarray,
        max_distance: float,
        results: set[tuple[int, int]]
    ):
        """Recursively query nodes intersecting a ray."""
        # Test ray against node bounds
        hit, t_min, t_max = node.bounds.intersect_ray(ray_origin, ray_dir)

        if not hit or t_min > max_distance:
            return

        if node.is_leaf():
            # Add all brush keys from this node
            results.update(node.brush_keys)
        else:
            # Query children
            for child in node.children:
                self._query_ray_recursive(child, ray_origin, ray_dir, max_distance, results)

    def query_aabb(self, aabb: AABB) -> list[tuple[int, int]]:
        """
        Query brushes that intersect an AABB.

        Args:
            aabb: Query bounding box

        Returns:
            List of brush keys that potentially intersect
        """
        results: set[tuple[int, int]] = set()
        self._query_aabb_recursive(self.root, aabb, results)
        return list(results)

    def _query_aabb_recursive(self, node: OctreeNode, aabb: AABB, results: set[tuple[int, int]]):
        """Recursively query nodes intersecting an AABB."""
        if not node.bounds.intersects(aabb):
            return

        if node.is_leaf():
            # Check each brush's actual bounds
            for brush_key in node.brush_keys:
                if brush_key in self._brush_bounds:
                    if self._brush_bounds[brush_key].intersects(aabb):
                        results.add(brush_key)
        else:
            for child in node.children:
                self._query_aabb_recursive(child, aabb, results)

    def query_point(self, point: np.ndarray) -> list[tuple[int, int]]:
        """
        Query brushes that contain a point.

        Args:
            point: Query point

        Returns:
            List of brush keys whose AABBs contain the point
        """
        point = np.asarray(point, dtype=np.float64)
        results: set[tuple[int, int]] = set()
        self._query_point_recursive(self.root, point, results)
        return list(results)

    def _query_point_recursive(self, node: OctreeNode, point: np.ndarray, results: set[tuple[int, int]]):
        """Recursively query nodes containing a point."""
        if not node.bounds.contains_point(point):
            return

        if node.is_leaf():
            for brush_key in node.brush_keys:
                if brush_key in self._brush_bounds:
                    if self._brush_bounds[brush_key].contains_point(point):
                        results.add(brush_key)
        else:
            # Only need to check one child
            child_idx = node.get_child_index(point)
            self._query_point_recursive(node.children[child_idx], point, results)

    def get_stats(self) -> dict:
        """Get statistics about the octree."""
        leaf_count = 0
        max_depth = 0
        max_items = 0
        total_items = 0

        def count_recursive(node: OctreeNode):
            nonlocal leaf_count, max_depth, max_items, total_items

            if node.is_leaf():
                leaf_count += 1
                max_depth = max(max_depth, node.depth)
                max_items = max(max_items, len(node.brush_keys))
                total_items += len(node.brush_keys)
            else:
                for child in node.children:
                    count_recursive(child)

        count_recursive(self.root)

        return {
            'brush_count': self._count,
            'leaf_nodes': leaf_count,
            'max_depth': max_depth,
            'max_items_per_leaf': max_items,
            'total_references': total_items,
            'avg_items_per_leaf': total_items / max(1, leaf_count)
        }

    def __len__(self) -> int:
        return self._count

    def __contains__(self, brush_key: tuple[int, int]) -> bool:
        return brush_key in self._brush_bounds
