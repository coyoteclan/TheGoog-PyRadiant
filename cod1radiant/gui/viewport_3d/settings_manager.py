"""Settings management for 3D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QSettings

from ...config import (
    COLORS,
    DEFAULT_CAMERA_SPEED,
    DEFAULT_MOUSE_SENSITIVITY,
    DEFAULT_FOV,
    DEFAULT_NEAR_PLANE,
    DEFAULT_FAR_PLANE,
)

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class SettingsManager:
    """Manages settings and colors for the 3D viewport."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport
        self._settings = QSettings("CoD1Radiant", "Editor")

        # Color attributes (initialized by load_colors)
        self.bg_color: tuple = COLORS["background_3d"]
        self.grid_color: tuple = COLORS["grid_major"]
        self.selection_color: tuple = COLORS["selection"]
        self.brush_outline_color: tuple = COLORS["brush_outline"]
        self.vao_color: tuple = (0.6, 0.6, 0.6, 1.0)

        # Grid/Axis settings
        self.show_grid: bool = True
        self.show_axis: bool = True
        self.axis_thickness: float = 2.0

        # Rendering settings
        self.face_culling: bool = True
        self.solid_depth_test: bool = True
        self.wireframe_overlay: bool = True
        self.backface_culling_3d: bool = True
        self.wireframe_depth_test: bool = True
        self.wireframe_thickness: float = 1.0

        # Entity display settings
        self.entity_markers_enabled: bool = True
        self.entity_marker_size: float = 16.0

        # Performance settings
        self.culling_enabled: bool = True
        self.batching_enabled: bool = True
        self.octree_enabled: bool = True

    def load_camera_settings(self):
        """Load camera settings from QSettings."""
        camera = self.viewport.camera
        camera.move_speed = self._settings.value(
            "viewport/cameraSpeed", DEFAULT_CAMERA_SPEED, type=float
        )
        camera.mouse_sensitivity = self._settings.value(
            "viewport/mouseSensitivity", DEFAULT_MOUSE_SENSITIVITY, type=float
        )
        camera.fov = self._settings.value(
            "viewport/fov", DEFAULT_FOV, type=float
        )
        camera.near = self._settings.value(
            "viewport/nearPlane", DEFAULT_NEAR_PLANE, type=float
        )
        camera.far = self._settings.value(
            "viewport/farPlane", DEFAULT_FAR_PLANE, type=float
        )

    def load_colors(self):
        """Load colors from settings."""
        # Background color
        self.bg_color = self._get_color_tuple("colors/background3d", COLORS["background_3d"])

        # Grid settings
        self.show_grid = self._settings.value("colors/grid3dEnabled", True, type=bool)
        self.grid_color = self._get_color_tuple("colors/grid3dColor", COLORS["grid_major"])

        # Axis settings
        self.show_axis = self._settings.value("viewport/axis3dEnabled", True, type=bool)
        self.axis_thickness = self._settings.value("viewport/axis3dThickness", 2.0, type=float)

        # Selection and brush colors
        self.selection_color = self._get_color_tuple("colors/selection", COLORS["selection"])
        self.brush_outline_color = self._get_color_tuple("colors/brushOutline", COLORS["brush_outline"])
        self.vao_color = self._get_color_tuple("colors/vaoColor", (0.6, 0.6, 0.6, 1.0))

        # 3D View Rendering settings
        self.face_culling = self._settings.value("render/faceCulling", True, type=bool)
        self.solid_depth_test = self._settings.value("render/solidDepthTest", True, type=bool)

        # Wireframe settings
        self.wireframe_overlay = self._settings.value("render/wireframeOverlay", True, type=bool)
        self.backface_culling_3d = self._settings.value("render/wireframeBackfaceCulling", True, type=bool)
        self.wireframe_depth_test = self._settings.value("render/wireframeDepthTest", True, type=bool)
        self.wireframe_thickness = self._settings.value("render/wireframeThickness", 1.0, type=float)

        # Entity display settings
        self.entity_markers_enabled = self._settings.value("render/entityMarkers", True, type=bool)
        self.entity_marker_size = self._settings.value("render/entityMarkerSize", 16.0, type=float)

        # Performance optimization settings
        self.culling_enabled = self._settings.value("performance/frustumCulling", True, type=bool)
        self.batching_enabled = self._settings.value("performance/batchedRendering", True, type=bool)
        self.octree_enabled = self._settings.value("performance/octreePicking", True, type=bool)

    def _get_color_tuple(self, key: str, default: tuple) -> tuple:
        """Get a color tuple from settings."""
        value = self._settings.value(key)
        if value is not None:
            try:
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    r, g, b = float(value[0]), float(value[1]), float(value[2])
                    a = float(value[3]) if len(value) > 3 else 1.0
                    return (r, g, b, a)
                elif isinstance(value, str):
                    parts = value.strip("()[]").split(",")
                    if len(parts) >= 3:
                        r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                        a = float(parts[3]) if len(parts) > 3 else 1.0
                        return (r, g, b, a)
            except (ValueError, TypeError, IndexError):
                pass
        return default

    def reload(self):
        """Reload all settings."""
        self.load_camera_settings()
        self.load_colors()
