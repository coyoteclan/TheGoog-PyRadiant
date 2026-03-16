"""
Brush Operations - Geometric computations for Brush objects.

This module provides functions for:
- Computing brush vertices from plane intersections
- Bounding box calculation
- Ray-brush intersection for picking
- Face area calculation

All functions work with the new parser classes (Vec3-based).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..io.map_parser.brush import Brush, BrushPlane

from ..io.map_parser.math import Vec3

# Small epsilon for floating point comparisons
EPSILON = 1e-6


# =============================================================================
# Vertex Computation
# =============================================================================

def compute_brush_vertices(brush: "Brush") -> dict[int, list[Vec3]]:
    """
    Compute vertices for all faces by intersecting planes.

    For each combination of 3 faces, compute the intersection point.
    A point is valid if it lies on or inside all other planes.

    Args:
        brush: The brush to compute vertices for

    Returns:
        Dictionary mapping face index (plane index) to list of vertices
    """
    planes = brush.planes
    n_planes = len(planes)

    if n_planes < 4:
        return {}  # Need at least 4 planes for a valid brush

    face_vertices: dict[int, list[Vec3]] = {i: [] for i in range(n_planes)}

    # Pre-compute all plane normals and distances
    plane_data: list[tuple[Vec3, float]] = []
    for plane in planes:
        normal = plane.normal
        distance = plane.distance
        plane_data.append((normal, distance))

    # Try all combinations of 3 planes
    for i in range(n_planes):
        n1, d1 = plane_data[i]
        for j in range(i + 1, n_planes):
            n2, d2 = plane_data[j]
            for k in range(j + 1, n_planes):
                n3, d3 = plane_data[k]

                # Find intersection point (Cramer's rule)
                n2_cross_n3 = n2.cross(n3)
                det = n1.dot(n2_cross_n3)

                if abs(det) < EPSILON:
                    continue  # Planes are parallel or degenerate

                n3_cross_n1 = n3.cross(n1)
                n1_cross_n2 = n1.cross(n2)
                inv_det = 1.0 / det

                # Compute intersection point
                point = (n2_cross_n3 * d1 + n3_cross_n1 * d2 + n1_cross_n2 * d3) * inv_det

                # Validate computed point
                if _is_invalid_vec3(point):
                    continue

                # Check if point is inside all planes
                # In CoD1 MAP format, normals point INWARD (toward brush interior),
                # so a valid vertex must be on the positive side (or on) all planes: dist >= -EPSILON
                is_valid = True
                for normal, distance in plane_data:
                    dist = point.dot(normal) - distance
                    if dist < -EPSILON:
                        is_valid = False
                        break

                if not is_valid:
                    continue

                # Add vertex to the 3 faces that created it
                for face_idx in (i, j, k):
                    # Check for duplicates
                    is_duplicate = False
                    for existing in face_vertices[face_idx]:
                        if _vec3_close(existing, point):
                            is_duplicate = True
                            break

                    if not is_duplicate:
                        face_vertices[face_idx].append(point.copy())

    # Sort vertices clockwise for each face
    for face_idx, vertices in face_vertices.items():
        if len(vertices) >= 3:
            normal = plane_data[face_idx][0]
            face_vertices[face_idx] = _sort_vertices_clockwise(vertices, normal)

    return face_vertices


def _sort_vertices_clockwise(vertices: list[Vec3], normal: Vec3) -> list[Vec3]:
    """Sort vertices clockwise when viewed from the direction of the normal."""
    if len(vertices) < 3:
        return vertices

    # Calculate centroid
    centroid = Vec3(
        sum(v.x for v in vertices) / len(vertices),
        sum(v.y for v in vertices) / len(vertices),
        sum(v.z for v in vertices) / len(vertices)
    )

    # Create local coordinate system
    # Find a vector not parallel to normal
    if abs(normal.x) < 0.9:
        up = Vec3(1.0, 0.0, 0.0)
    else:
        up = Vec3(0.0, 1.0, 0.0)

    u = normal.cross(up).normalize()
    v = normal.cross(u)

    # Calculate angles
    import math
    angles = []
    for vertex in vertices:
        rel = vertex - centroid
        angle = math.atan2(rel.dot(v), rel.dot(u))
        angles.append(angle)

    # Sort by angle (clockwise = descending)
    sorted_pairs = sorted(zip(angles, vertices), key=lambda x: x[0], reverse=True)
    return [v for _, v in sorted_pairs]


def _vec3_close(a: Vec3, b: Vec3, tol: float = EPSILON) -> bool:
    """Check if two Vec3 are approximately equal."""
    return (abs(a.x - b.x) < tol and
            abs(a.y - b.y) < tol and
            abs(a.z - b.z) < tol)


def _is_invalid_vec3(v: Vec3) -> bool:
    """Check if Vec3 contains NaN or Inf values."""
    import math
    return (math.isnan(v.x) or math.isnan(v.y) or math.isnan(v.z) or
            math.isinf(v.x) or math.isinf(v.y) or math.isinf(v.z))


# =============================================================================
# Bounds Calculation
# =============================================================================

def get_brush_bounds(brush: "Brush") -> tuple[Vec3, Vec3] | None:
    """
    Calculate axis-aligned bounding box of the brush.

    Args:
        brush: The brush to calculate bounds for

    Returns:
        Tuple of (min_point, max_point) or None if brush has no valid vertices
    """
    face_vertices = compute_brush_vertices(brush)
    all_verts: list[Vec3] = []

    for vertices in face_vertices.values():
        all_verts.extend(vertices)

    if not all_verts:
        return None

    min_pt = Vec3(
        min(v.x for v in all_verts),
        min(v.y for v in all_verts),
        min(v.z for v in all_verts)
    )
    max_pt = Vec3(
        max(v.x for v in all_verts),
        max(v.y for v in all_verts),
        max(v.z for v in all_verts)
    )

    return min_pt, max_pt


def get_brush_center(brush: "Brush") -> Vec3:
    """
    Calculate the center point of the brush.

    Args:
        brush: The brush to calculate center for

    Returns:
        Center point (centroid of bounding box)
    """
    bounds = get_brush_bounds(brush)
    if bounds is None:
        return Vec3.zero()

    min_pt, max_pt = bounds
    return (min_pt + max_pt) * 0.5


def get_all_brush_vertices(brush: "Brush") -> list[Vec3]:
    """
    Get all unique vertices of the brush.

    Args:
        brush: The brush to get vertices from

    Returns:
        List of unique vertex positions
    """
    face_vertices = compute_brush_vertices(brush)
    all_vertices: list[Vec3] = []

    for vertices in face_vertices.values():
        for vertex in vertices:
            # Check for duplicates
            is_duplicate = False
            for existing in all_vertices:
                if _vec3_close(existing, vertex):
                    is_duplicate = True
                    break
            if not is_duplicate:
                all_vertices.append(vertex)

    return all_vertices


# =============================================================================
# Validation
# =============================================================================

def is_brush_valid(brush: "Brush", min_face_area: float = 1.0) -> tuple[bool, str]:
    """
    Check if a brush has valid geometry.

    Validates:
    - At least 4 planes
    - Each face has at least 3 vertices
    - Each face has sufficient area

    Args:
        brush: The brush to validate
        min_face_area: Minimum area for each face

    Returns:
        Tuple of (is_valid, error_message)
    """
    n_planes = len(brush.planes)

    if n_planes < 4:
        return False, f"Brush has only {n_planes} planes (minimum 4)"

    # Compute vertices
    face_vertices = compute_brush_vertices(brush)

    for face_idx, vertices in face_vertices.items():
        if len(vertices) < 3:
            return False, f"Face {face_idx} has only {len(vertices)} vertices (minimum 3)"

        # Check face area
        area = _compute_face_area(vertices)
        if area < min_face_area:
            return False, f"Face {face_idx} area {area:.2f} < minimum {min_face_area}"

    return True, "Valid"


def _compute_face_area(vertices: list[Vec3]) -> float:
    """Calculate the area of a face polygon using cross product method."""
    if len(vertices) < 3:
        return 0.0

    # Use cross product method for 3D polygon area
    total = Vec3.zero()
    n = len(vertices)

    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        cross = Vec3(
            v1.y * v2.z - v1.z * v2.y,
            v1.z * v2.x - v1.x * v2.z,
            v1.x * v2.y - v1.y * v2.x
        )
        total = total + cross

    return total.length() / 2.0


# =============================================================================
# Ray Intersection
# =============================================================================

def intersect_ray_brush(
    brush: "Brush",
    origin: Vec3,
    direction: Vec3
) -> float | None:
    """
    Find intersection of a ray with the brush.

    Uses AABB pre-check, then tests each face.

    Args:
        brush: The brush to test
        origin: Ray origin point
        direction: Ray direction (should be normalized)

    Returns:
        Distance to intersection or None if no hit
    """
    bounds = get_brush_bounds(brush)
    if bounds is None:
        return None

    min_pt, max_pt = bounds

    # AABB pre-check (slab method)
    t_min = 0.0
    t_max = float('inf')

    for i, (o, d, mn, mx) in enumerate([
        (origin.x, direction.x, min_pt.x, max_pt.x),
        (origin.y, direction.y, min_pt.y, max_pt.y),
        (origin.z, direction.z, min_pt.z, max_pt.z),
    ]):
        if abs(d) < EPSILON:
            if o < mn or o > mx:
                return None
        else:
            inv_d = 1.0 / d
            t1 = (mn - o) * inv_d
            t2 = (mx - o) * inv_d

            if t1 > t2:
                t1, t2 = t2, t1

            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

            if t_min > t_max:
                return None

    # AABB hit - now test each face
    face_vertices = compute_brush_vertices(brush)
    closest_t: float | None = None

    for face_idx, vertices in face_vertices.items():
        if len(vertices) < 3:
            continue

        plane = brush.planes[face_idx]
        normal = plane.normal
        distance = plane.distance

        # Ray-plane intersection
        denom = normal.dot(direction)
        if abs(denom) < EPSILON:
            continue

        t = (distance - normal.dot(origin)) / denom
        if t < 0:
            continue

        # Check if hit point is inside face polygon
        hit_point = origin + direction * t
        if _point_in_polygon(hit_point, vertices, normal):
            if closest_t is None or t < closest_t:
                closest_t = t

    return closest_t


def _point_in_polygon(point: Vec3, vertices: list[Vec3], normal: Vec3) -> bool:
    """Check if a point lies inside a convex polygon.

    Vertices are sorted clockwise when viewed from the normal direction.
    For clockwise winding, the cross product of (edge x to_point) should point
    in the OPPOSITE direction of the normal (negative dot product) for points inside.
    """
    n = len(vertices)
    if n < 3:
        return False

    for i in range(n):
        v1 = vertices[i]
        v2 = vertices[(i + 1) % n]
        edge = v2 - v1
        to_point = point - v1
        cross = edge.cross(to_point)

        # For clockwise vertices, inside points have cross.dot(normal) <= 0
        # We use > EPSILON to reject points clearly outside
        if cross.dot(normal) > EPSILON:
            return False

    return True


# =============================================================================
# Face Operations
# =============================================================================

def get_face_center(vertices: list[Vec3]) -> Vec3:
    """
    Get center point of a face from its vertices.

    Args:
        vertices: List of face vertices

    Returns:
        Center point of the face
    """
    if not vertices:
        return Vec3.zero()

    return Vec3(
        sum(v.x for v in vertices) / len(vertices),
        sum(v.y for v in vertices) / len(vertices),
        sum(v.z for v in vertices) / len(vertices)
    )


def get_face_normal(plane: "BrushPlane") -> Vec3:
    """
    Get the normal vector of a face from its plane.

    Args:
        plane: The BrushPlane

    Returns:
        Unit normal vector
    """
    return plane.normal
