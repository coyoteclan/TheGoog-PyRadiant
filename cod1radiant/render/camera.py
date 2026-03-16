"""3D Camera for viewport navigation."""

from __future__ import annotations

import numpy as np
from dataclasses import dataclass, field
import math


@dataclass
class Camera:
    """First-person style camera for 3D viewport."""

    # Position
    position: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0, 64.0]))

    # Rotation (in degrees)
    yaw: float = -90.0  # Look along -Y by default (like Radiant)
    pitch: float = 0.0

    # Movement settings
    move_speed: float = 500.0
    mouse_sensitivity: float = 0.2

    # Projection settings
    fov: float = 90.0
    near: float = 1.0
    far: float = 16384.0
    aspect: float = 1.0

    def __post_init__(self):
        self.position = np.asarray(self.position, dtype=np.float32)
        self._update_vectors()

    def _update_vectors(self):
        """Update direction vectors from yaw/pitch."""
        yaw_rad = math.radians(self.yaw)
        pitch_rad = math.radians(self.pitch)

        # Forward vector
        self.forward = np.array([
            math.cos(pitch_rad) * math.cos(yaw_rad),
            math.cos(pitch_rad) * math.sin(yaw_rad),
            math.sin(pitch_rad)
        ], dtype=np.float32)

        # Right vector (cross product of forward and world up)
        world_up = np.array([0.0, 0.0, 1.0], dtype=np.float32)
        self.right = np.cross(self.forward, world_up)
        right_len = np.linalg.norm(self.right)
        if right_len > 1e-6:
            self.right = self.right / right_len
        else:
            # Handle edge case when looking straight up/down
            self.right = np.array([1.0, 0.0, 0.0], dtype=np.float32)

        # Up vector
        self.up = np.cross(self.right, self.forward)
        up_len = np.linalg.norm(self.up)
        if up_len > 1e-6:
            self.up = self.up / up_len
        else:
            self.up = np.array([0.0, 0.0, 1.0], dtype=np.float32)

    def rotate(self, delta_yaw: float, delta_pitch: float):
        """Rotate camera by mouse movement."""
        self.yaw += delta_yaw * self.mouse_sensitivity
        self.pitch += delta_pitch * self.mouse_sensitivity

        # Clamp pitch to avoid gimbal lock
        self.pitch = max(-89.0, min(89.0, self.pitch))

        self._update_vectors()

    def move_forward(self, delta: float):
        """Move camera forward/backward."""
        self.position += self.forward * delta * self.move_speed

    def move_right(self, delta: float):
        """Move camera left/right."""
        self.position += self.right * delta * self.move_speed

    def move_up(self, delta: float):
        """Move camera up/down (world Z axis)."""
        self.position[2] += delta * self.move_speed

    def get_view_matrix(self) -> np.ndarray:
        """Get the view matrix (4x4)."""
        f = self.forward
        r = self.right
        u = self.up

        # Standard view matrix (row-major, will be transposed when sent to OpenGL)
        view = np.array([
            [r[0], r[1], r[2], -np.dot(r, self.position)],
            [u[0], u[1], u[2], -np.dot(u, self.position)],
            [-f[0], -f[1], -f[2], np.dot(f, self.position)],
            [0.0, 0.0, 0.0, 1.0]
        ], dtype=np.float32)

        return view

    def get_projection_matrix(self) -> np.ndarray:
        """Get the perspective projection matrix (4x4)."""
        fov_rad = math.radians(self.fov)
        f = 1.0 / math.tan(fov_rad / 2.0)

        # Standard perspective matrix (row-major)
        proj = np.zeros((4, 4), dtype=np.float32)
        proj[0, 0] = f / self.aspect
        proj[1, 1] = f
        proj[2, 2] = (self.far + self.near) / (self.near - self.far)
        proj[2, 3] = (2.0 * self.far * self.near) / (self.near - self.far)
        proj[3, 2] = -1.0

        return proj

    def get_view_projection_matrix(self) -> np.ndarray:
        """Get combined view-projection matrix."""
        return self.get_projection_matrix() @ self.get_view_matrix()

    def set_aspect(self, width: int, height: int):
        """Update aspect ratio."""
        if height > 0:
            self.aspect = width / height

    def look_at(self, target: np.ndarray):
        """Point camera at a target position."""
        direction = target - self.position
        length = np.linalg.norm(direction)

        if length < 0.001:
            return

        direction = direction / length

        self.pitch = math.degrees(math.asin(direction[2]))
        self.yaw = math.degrees(math.atan2(direction[1], direction[0]))

        self._update_vectors()

    def reset(self):
        """Reset camera to default position."""
        self.position = np.array([0.0, -256.0, 128.0], dtype=np.float32)
        self.yaw = 90.0
        self.pitch = -15.0
        self._update_vectors()

    def screen_to_ray(self, screen_x: float, screen_y: float,
                      viewport_width: int, viewport_height: int) -> tuple[np.ndarray, np.ndarray]:
        """
        Convert screen coordinates to a ray in world space.

        Args:
            screen_x: X coordinate in pixels (0 = left)
            screen_y: Y coordinate in pixels (0 = top)
            viewport_width: Width of the viewport in pixels
            viewport_height: Height of the viewport in pixels

        Returns:
            Tuple of (ray_origin, ray_direction) as numpy arrays
        """
        # Convert screen coords to normalized device coordinates (-1 to 1)
        ndc_x = (2.0 * screen_x / viewport_width) - 1.0
        ndc_y = 1.0 - (2.0 * screen_y / viewport_height)  # Flip Y

        # Calculate ray direction in view space
        fov_rad = math.radians(self.fov)
        tan_half_fov = math.tan(fov_rad / 2.0)

        # Ray direction in camera space
        ray_x = ndc_x * self.aspect * tan_half_fov
        ray_y = ndc_y * tan_half_fov
        ray_z = 1.0  # Forward

        # Transform to world space
        ray_dir = (
            ray_x * self.right +
            ray_y * self.up +
            ray_z * self.forward
        )
        ray_dir = ray_dir / np.linalg.norm(ray_dir)

        return self.position.copy(), ray_dir.astype(np.float64)
