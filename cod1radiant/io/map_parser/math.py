"""
CoD1 Map Parser - Math Module
=============================

Vector and color classes for 3D coordinate manipulation.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple


@dataclass
class Vec3:
    """3D Vector class for coordinates and directions."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: 'Vec3') -> 'Vec3':
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __truediv__(self, scalar: float) -> 'Vec3':
        return Vec3(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> 'Vec3':
        return Vec3(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vec3):
            return False
        return (abs(self.x - other.x) < 1e-6 and
                abs(self.y - other.y) < 1e-6 and
                abs(self.z - other.z) < 1e-6)

    def __hash__(self) -> int:
        return hash((round(self.x, 6), round(self.y, 6), round(self.z, 6)))

    def dot(self, other: 'Vec3') -> float:
        """Dot product."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: 'Vec3') -> 'Vec3':
        """Cross product."""
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x
        )

    def length(self) -> float:
        """Vector length/magnitude."""
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    def length_squared(self) -> float:
        """Squared length (faster, avoids sqrt)."""
        return self.x**2 + self.y**2 + self.z**2

    def normalize(self) -> 'Vec3':
        """Return normalized vector."""
        length = self.length()
        if length < 1e-10:
            return Vec3(0, 0, 0)
        return self / length

    def copy(self) -> 'Vec3':
        """Create a copy."""
        return Vec3(self.x, self.y, self.z)

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def to_array(self) -> 'np.ndarray':
        """Convert to numpy array for GPU operations."""
        import numpy as np
        return np.array([self.x, self.y, self.z], dtype=np.float32)

    @classmethod
    def from_array(cls, arr: 'np.ndarray') -> 'Vec3':
        """Create Vec3 from numpy array."""
        return cls(float(arr[0]), float(arr[1]), float(arr[2]))

    def to_string(self, precision: int = 6) -> str:
        """Convert to space-separated string."""
        def fmt(v: float) -> str:
            if abs(v - round(v)) < 1e-6:
                return str(int(round(v)))
            return f"{v:.{precision}f}".rstrip('0').rstrip('.')
        return f"{fmt(self.x)} {fmt(self.y)} {fmt(self.z)}"

    @classmethod
    def from_string(cls, s: str) -> 'Vec3':
        """Parse from space-separated string."""
        parts = s.strip().split()
        if len(parts) >= 3:
            return cls(float(parts[0]), float(parts[1]), float(parts[2]))
        raise ValueError(f"Invalid Vec3 string: {s}")

    @classmethod
    def zero(cls) -> 'Vec3':
        """Return zero vector."""
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def one(cls) -> 'Vec3':
        """Return unit vector (1,1,1)."""
        return cls(1.0, 1.0, 1.0)

    def __repr__(self) -> str:
        return f"Vec3({self.x}, {self.y}, {self.z})"

    def __str__(self) -> str:
        return self.to_string()


@dataclass
class Color:
    """RGBA Color class."""
    r: int = 255
    g: int = 255
    b: int = 255
    a: int = 255

    def to_tuple(self) -> Tuple[int, int, int, int]:
        return (self.r, self.g, self.b, self.a)

    def to_string(self) -> str:
        return f"{self.r} {self.g} {self.b} {self.a}"

    @classmethod
    def from_values(cls, r: int, g: int, b: int, a: int = 255) -> 'Color':
        return cls(
            max(0, min(255, r)),
            max(0, min(255, g)),
            max(0, min(255, b)),
            max(0, min(255, a))
        )

    @classmethod
    def white(cls) -> 'Color':
        return cls(255, 255, 255, 255)

    @classmethod
    def black(cls) -> 'Color':
        return cls(0, 0, 0, 255)

    def copy(self) -> 'Color':
        return Color(self.r, self.g, self.b, self.a)

    def __repr__(self) -> str:
        return f"Color({self.r}, {self.g}, {self.b}, {self.a})"
