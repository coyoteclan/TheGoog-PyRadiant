"""Settings/Preferences dialog for CoD1 Radiant Editor."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QSettings, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QDialogButtonBox,
)

from ...config import (
    DEFAULT_GRID_SIZE,
    DEFAULT_NEAR_PLANE,
    DEFAULT_FAR_PLANE,
    DEFAULT_FOV,
    DEFAULT_CAMERA_SPEED,
    DEFAULT_MOUSE_SENSITIVITY,
    COLORS,
    BRUSH_COLORS_2D,
)
from .settings_tabs import (
    GeneralTab,
    ViewportTab,
    ColorsTab,
    ShaderTab,
    KeybindingsTab,
    ColorButton,
    rgba_to_qcolor,
    rgb_to_qcolor,
    qcolor_to_rgba,
    qcolor_to_rgb,
)


class SettingsDialog(QDialog):
    """Settings/Preferences dialog with multiple tabs."""

    settings_changed = pyqtSignal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._settings = QSettings("CoD1Radiant", "Editor")
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Preferences")
        self.setMinimumSize(800, 700)
        self.resize(800, 700)

        layout = QVBoxLayout(self)

        # Tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create tabs using modular components
        self.general_tab = GeneralTab()
        self.viewport_tab = ViewportTab()
        self.colors_tab = ColorsTab()
        self.shader_tab = ShaderTab()
        self.keybindings_tab = KeybindingsTab()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.viewport_tab, "Viewport")
        self.tabs.addTab(self.colors_tab, "Colors")
        self.tabs.addTab(self.shader_tab, "Shader")
        self.tabs.addTab(self.keybindings_tab, "Keybindings")

        # Button box
        button_box = QDialogButtonBox()
        self.ok_button = button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        self.apply_button = button_box.addButton(QDialogButtonBox.StandardButton.Apply)
        self.cancel_button = button_box.addButton(QDialogButtonBox.StandardButton.Cancel)
        self.reset_button = button_box.addButton("Reset to Defaults", QDialogButtonBox.ButtonRole.ResetRole)

        self.ok_button.clicked.connect(self._on_ok)
        self.apply_button.clicked.connect(self._on_apply)
        self.cancel_button.clicked.connect(self.reject)
        self.reset_button.clicked.connect(self._reset_to_defaults)

        layout.addWidget(button_box)

        # Expose tab widgets for settings access
        self._expose_tab_widgets()

    def _expose_tab_widgets(self) -> None:
        """Expose tab widgets as dialog attributes for settings load/save."""
        # General tab
        self.grid_size_combo = self.general_tab.grid_size_combo
        self.undo_levels_spin = self.general_tab.undo_levels_spin
        self.load_last_map_check = self.general_tab.load_last_map_check
        self.game_path_edit = self.general_tab.game_path_edit
        self.texture_path_edit = self.general_tab.texture_path_edit
        self.xmodel_path_edit = self.general_tab.xmodel_path_edit
        self.autosave_enabled_check = self.general_tab.autosave_enabled_check
        self.autosave_interval_spin = self.general_tab.autosave_interval_spin
        self.recent_files_spin = self.general_tab.recent_files_spin
        self.rotation_angle_spin = self.general_tab.rotation_angle_spin
        self.scale_factor_spin = self.general_tab.scale_factor_spin
        self.clone_offset_x_spin = self.general_tab.clone_offset_x_spin
        self.clone_offset_y_spin = self.general_tab.clone_offset_y_spin
        self.clone_offset_z_spin = self.general_tab.clone_offset_z_spin

        # Viewport tab
        self.fov_spin = self.viewport_tab.fov_spin
        self.near_plane_spin = self.viewport_tab.near_plane_spin
        self.far_plane_spin = self.viewport_tab.far_plane_spin
        self.camera_speed_spin = self.viewport_tab.camera_speed_spin
        self.mouse_sensitivity_spin = self.viewport_tab.mouse_sensitivity_spin
        self.zoom_speed_3d_spin = self.viewport_tab.zoom_speed_3d_spin
        self.invert_mouse_y_check = self.viewport_tab.invert_mouse_y_check
        self.invert_mouse_x_check = self.viewport_tab.invert_mouse_x_check
        self.show_axis_3d_check = self.viewport_tab.show_axis_3d_check
        self.default_view_combo = self.viewport_tab.default_view_combo
        self.zoom_speed_2d_spin = self.viewport_tab.zoom_speed_2d_spin
        self.pan_speed_spin = self.viewport_tab.pan_speed_spin
        self.show_grid_check = self.viewport_tab.show_grid_check
        self.show_axis_labels_check = self.viewport_tab.show_axis_labels_check
        self.snap_to_grid_check = self.viewport_tab.snap_to_grid_check
        self.show_axis_2d_check = self.viewport_tab.show_axis_2d_check

        # Colors tab
        self.theme_combo = self.colors_tab.theme_combo
        self.density_combo = self.colors_tab.density_combo
        self.console_color_button = self.colors_tab.console_color_button
        self.custom_stylesheet_edit = self.colors_tab.custom_stylesheet_edit
        self.custom_stylesheet_browse = self.colors_tab.custom_stylesheet_browse
        self.bg_2d_button = self.colors_tab.bg_2d_button
        self.grid_major_button = self.colors_tab.grid_major_button
        self.grid_minor_button = self.colors_tab.grid_minor_button
        self.bg_3d_button = self.colors_tab.bg_3d_button
        self.grid_3d_enabled = self.colors_tab.grid_3d_enabled
        self.grid_3d_color_button = self.colors_tab.grid_3d_color_button
        self.axis_3d_enabled = self.colors_tab.axis_3d_enabled
        self.axis_3d_thickness = self.colors_tab.axis_3d_thickness
        self.selection_button = self.colors_tab.selection_button
        self.brush_outline_button = self.colors_tab.brush_outline_button
        self.vao_color_button = self.colors_tab.vao_color_button
        self.brush_structural_button = self.colors_tab.brush_structural_button
        self.brush_detail_button = self.colors_tab.brush_detail_button
        self.brush_weapon_clip_button = self.colors_tab.brush_weapon_clip_button
        self.brush_non_colliding_button = self.colors_tab.brush_non_colliding_button
        self.brush_curves_button = self.colors_tab.brush_curves_button
        self.brush_terrain_button = self.colors_tab.brush_terrain_button

        # Shader tab
        self.face_culling_check = self.shader_tab.face_culling_check
        self.solid_depth_test_check = self.shader_tab.solid_depth_test_check
        self.backface_culling_2d_check = self.shader_tab.backface_culling_2d_check
        self.wireframe_overlay_check = self.shader_tab.wireframe_overlay_check
        self.backface_culling_3d_check = self.shader_tab.backface_culling_3d_check
        self.wireframe_depth_test_check = self.shader_tab.wireframe_depth_test_check
        self.wireframe_thickness_spin = self.shader_tab.wireframe_thickness_spin
        self.entity_markers_check = self.shader_tab.entity_markers_check
        self.entity_marker_size_spin = self.shader_tab.entity_marker_size_spin
        self.frustum_culling_check = self.shader_tab.frustum_culling_check
        self.batched_rendering_check = self.shader_tab.batched_rendering_check
        self.octree_picking_check = self.shader_tab.octree_picking_check

        # Keybindings tab
        self.keybindings_table = self.keybindings_tab.keybindings_table

    def _load_settings(self) -> None:
        """Load current settings into the UI."""
        # General tab - Editor
        grid_size = self._settings.value("editor/gridSize", DEFAULT_GRID_SIZE, type=int)
        index = self.grid_size_combo.findData(grid_size)
        if index >= 0:
            self.grid_size_combo.setCurrentIndex(index)

        self.undo_levels_spin.setValue(
            self._settings.value("editor/undoLevels", 100, type=int)
        )
        self.load_last_map_check.setChecked(
            self._settings.value("editor/loadLastMap", False, type=bool)
        )

        # General tab - Paths
        self.game_path_edit.setText(
            self._settings.value("paths/gamePath", "", type=str)
        )
        self.texture_path_edit.setText(
            self._settings.value("paths/texturePath", "", type=str)
        )
        self.xmodel_path_edit.setText(
            self._settings.value("paths/xmodelPath", "", type=str)
        )

        # General tab - Auto-Save
        self.autosave_enabled_check.setChecked(
            self._settings.value("editor/autosaveEnabled", False, type=bool)
        )
        self.autosave_interval_spin.setValue(
            self._settings.value("editor/autosaveInterval", 5, type=int)
        )
        self.recent_files_spin.setValue(
            self._settings.value("editor/recentFilesCount", 10, type=int)
        )

        # General tab - Transformations
        self.rotation_angle_spin.setValue(
            self._settings.value("editor/rotationAngle", 15.0, type=float)
        )
        self.scale_factor_spin.setValue(
            self._settings.value("editor/scaleFactor", 1.1, type=float)
        )
        self.clone_offset_x_spin.setValue(
            self._settings.value("editor/cloneOffsetX", 16, type=int)
        )
        self.clone_offset_y_spin.setValue(
            self._settings.value("editor/cloneOffsetY", 16, type=int)
        )
        self.clone_offset_z_spin.setValue(
            self._settings.value("editor/cloneOffsetZ", 0, type=int)
        )

        # Viewport tab - 3D Camera
        self.fov_spin.setValue(
            self._settings.value("viewport/fov", DEFAULT_FOV, type=float)
        )
        self.near_plane_spin.setValue(
            self._settings.value("viewport/nearPlane", DEFAULT_NEAR_PLANE, type=float)
        )
        self.far_plane_spin.setValue(
            self._settings.value("viewport/farPlane", DEFAULT_FAR_PLANE, type=float)
        )
        self.camera_speed_spin.setValue(
            self._settings.value("viewport/cameraSpeed", DEFAULT_CAMERA_SPEED, type=float)
        )
        self.mouse_sensitivity_spin.setValue(
            self._settings.value("viewport/mouseSensitivity", DEFAULT_MOUSE_SENSITIVITY, type=float)
        )
        self.zoom_speed_3d_spin.setValue(
            self._settings.value("viewport/zoomSpeed3d", 1.0, type=float)
        )
        self.invert_mouse_y_check.setChecked(
            self._settings.value("viewport/invertMouseY", False, type=bool)
        )
        self.invert_mouse_x_check.setChecked(
            self._settings.value("viewport/invertMouseX", False, type=bool)
        )
        self.show_axis_3d_check.setChecked(
            self._settings.value("viewport/showAxis3d", True, type=bool)
        )

        # Viewport tab - 2D View
        default_view = self._settings.value("viewport/defaultView", "xy", type=str)
        index = self.default_view_combo.findData(default_view)
        if index >= 0:
            self.default_view_combo.setCurrentIndex(index)

        self.zoom_speed_2d_spin.setValue(
            self._settings.value("viewport/zoomSpeed2d", 1.0, type=float)
        )
        self.pan_speed_spin.setValue(
            self._settings.value("viewport/panSpeed", 1.0, type=float)
        )
        self.show_grid_check.setChecked(
            self._settings.value("viewport/showGrid", True, type=bool)
        )
        self.show_axis_labels_check.setChecked(
            self._settings.value("viewport/showAxisLabels", True, type=bool)
        )
        self.snap_to_grid_check.setChecked(
            self._settings.value("editor/snapToGrid", True, type=bool)
        )
        self.show_axis_2d_check.setChecked(
            self._settings.value("viewport/showAxis2d", True, type=bool)
        )

        # Colors tab
        theme = self._settings.value("colors/theme", "dark", type=str)
        index = self.theme_combo.findData(theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        density = self._settings.value("colors/uiDensity", "semi_compact", type=str)
        index = self.density_combo.findData(density)
        if index >= 0:
            self.density_combo.setCurrentIndex(index)

        custom_stylesheet = self._settings.value("colors/customStylesheet", "", type=str)
        self.custom_stylesheet_edit.setText(custom_stylesheet)

        is_custom = (theme == "custom")
        self.custom_stylesheet_edit.setEnabled(is_custom)
        self.custom_stylesheet_browse.setEnabled(is_custom)

        # 2D View colors
        self._load_color_setting("colors/background2d", self.bg_2d_button, COLORS["background_2d"])
        self._load_color_setting("colors/gridMajor", self.grid_major_button, COLORS["grid_major"])
        self._load_color_setting("colors/gridMinor", self.grid_minor_button, COLORS["grid_minor"])

        # 3D View colors
        self._load_color_setting("colors/background3d", self.bg_3d_button, COLORS["background_3d"])
        self.grid_3d_enabled.setChecked(
            self._settings.value("colors/grid3dEnabled", True, type=bool)
        )
        self._load_color_setting("colors/grid3dColor", self.grid_3d_color_button, COLORS["grid_major"])
        self.axis_3d_enabled.setChecked(
            self._settings.value("viewport/axis3dEnabled", True, type=bool)
        )
        self.axis_3d_thickness.setValue(
            self._settings.value("viewport/axis3dThickness", 2.0, type=float)
        )

        # Selection colors
        self._load_color_setting("colors/selection", self.selection_button, COLORS["selection"])
        self._load_color_setting("colors/brushOutline", self.brush_outline_button, COLORS["brush_outline"])
        self._load_color_setting("colors/vaoColor", self.vao_color_button, (0.6, 0.6, 0.6, 1.0))

        # Editor colors
        self._load_color_setting("colors/console", self.console_color_button, (0.12, 0.12, 0.12, 1.0))

        # 2D Brush Colors
        self._load_color_setting("colors/brush2d/structural", self.brush_structural_button, BRUSH_COLORS_2D["structural"])
        self._load_color_setting("colors/brush2d/detail", self.brush_detail_button, BRUSH_COLORS_2D["detail"])
        self._load_color_setting("colors/brush2d/weaponClip", self.brush_weapon_clip_button, BRUSH_COLORS_2D["weapon_clip"])
        self._load_color_setting("colors/brush2d/nonColliding", self.brush_non_colliding_button, BRUSH_COLORS_2D["non_colliding"])
        self._load_color_setting("colors/brush2d/curves", self.brush_curves_button, BRUSH_COLORS_2D["curves"])
        self._load_color_setting("colors/brush2d/terrain", self.brush_terrain_button, BRUSH_COLORS_2D["terrain"])

        # Shader tab - 3D View Rendering
        self.face_culling_check.setChecked(
            self._settings.value("render/faceCulling", True, type=bool)
        )
        self.solid_depth_test_check.setChecked(
            self._settings.value("render/solidDepthTest", True, type=bool)
        )

        # Wireframe settings
        self.wireframe_overlay_check.setChecked(
            self._settings.value("render/wireframeOverlay", True, type=bool)
        )
        self.backface_culling_3d_check.setChecked(
            self._settings.value("render/wireframeBackfaceCulling", True, type=bool)
        )
        self.wireframe_depth_test_check.setChecked(
            self._settings.value("render/wireframeDepthTest", True, type=bool)
        )
        self.wireframe_thickness_spin.setValue(
            self._settings.value("render/wireframeThickness", 1.0, type=float)
        )

        # 2D View
        self.backface_culling_2d_check.setChecked(
            self._settings.value("render/backfaceCulling2d", True, type=bool)
        )

        # Entity Display
        self.entity_markers_check.setChecked(
            self._settings.value("render/entityMarkers", True, type=bool)
        )
        self.entity_marker_size_spin.setValue(
            self._settings.value("render/entityMarkerSize", 16.0, type=float)
        )

        # Performance Optimizations
        self.frustum_culling_check.setChecked(
            self._settings.value("performance/frustumCulling", True, type=bool)
        )
        self.batched_rendering_check.setChecked(
            self._settings.value("performance/batchedRendering", True, type=bool)
        )
        self.octree_picking_check.setChecked(
            self._settings.value("performance/octreePicking", True, type=bool)
        )

    def _load_color_setting(self, key: str, button: ColorButton, default: tuple) -> None:
        """Load a color setting from QSettings."""
        value = self._settings.value(key)
        if value is not None:
            try:
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    button.setColor(rgba_to_qcolor(tuple(float(x) for x in value)))
                    return
            except (ValueError, TypeError):
                pass
        button.setColor(rgba_to_qcolor(default))

    def _save_settings(self) -> None:
        """Save current UI values to settings."""
        # General tab - Editor
        self._settings.setValue("editor/gridSize", self.grid_size_combo.currentData())
        self._settings.setValue("editor/undoLevels", self.undo_levels_spin.value())
        self._settings.setValue("editor/loadLastMap", self.load_last_map_check.isChecked())

        # General tab - Paths
        self._settings.setValue("paths/gamePath", self.game_path_edit.text())
        self._settings.setValue("paths/texturePath", self.texture_path_edit.text())
        self._settings.setValue("paths/xmodelPath", self.xmodel_path_edit.text())

        # General tab - Auto-Save
        self._settings.setValue("editor/autosaveEnabled", self.autosave_enabled_check.isChecked())
        self._settings.setValue("editor/autosaveInterval", self.autosave_interval_spin.value())
        self._settings.setValue("editor/recentFilesCount", self.recent_files_spin.value())

        # General tab - Transformations
        self._settings.setValue("editor/rotationAngle", self.rotation_angle_spin.value())
        self._settings.setValue("editor/scaleFactor", self.scale_factor_spin.value())
        self._settings.setValue("editor/cloneOffsetX", self.clone_offset_x_spin.value())
        self._settings.setValue("editor/cloneOffsetY", self.clone_offset_y_spin.value())
        self._settings.setValue("editor/cloneOffsetZ", self.clone_offset_z_spin.value())

        # Viewport tab - 3D Camera
        self._settings.setValue("viewport/fov", self.fov_spin.value())
        self._settings.setValue("viewport/nearPlane", self.near_plane_spin.value())
        self._settings.setValue("viewport/farPlane", self.far_plane_spin.value())
        self._settings.setValue("viewport/cameraSpeed", self.camera_speed_spin.value())
        self._settings.setValue("viewport/mouseSensitivity", self.mouse_sensitivity_spin.value())
        self._settings.setValue("viewport/zoomSpeed3d", self.zoom_speed_3d_spin.value())
        self._settings.setValue("viewport/invertMouseY", self.invert_mouse_y_check.isChecked())
        self._settings.setValue("viewport/invertMouseX", self.invert_mouse_x_check.isChecked())
        self._settings.setValue("viewport/showAxis3d", self.show_axis_3d_check.isChecked())

        # Viewport tab - 2D View
        self._settings.setValue("editor/snapToGrid", self.snap_to_grid_check.isChecked())
        self._settings.setValue("viewport/defaultView", self.default_view_combo.currentData())
        self._settings.setValue("viewport/zoomSpeed2d", self.zoom_speed_2d_spin.value())
        self._settings.setValue("viewport/panSpeed", self.pan_speed_spin.value())
        self._settings.setValue("viewport/showGrid", self.show_grid_check.isChecked())
        self._settings.setValue("viewport/showAxisLabels", self.show_axis_labels_check.isChecked())
        self._settings.setValue("viewport/showAxis2d", self.show_axis_2d_check.isChecked())

        # Colors tab
        self._settings.setValue("colors/theme", self.theme_combo.currentData())
        self._settings.setValue("colors/uiDensity", self.density_combo.currentData())
        self._settings.setValue("colors/customStylesheet", self.custom_stylesheet_edit.text())

        # 2D View colors
        self._settings.setValue("colors/background2d", qcolor_to_rgba(self.bg_2d_button.color()))
        self._settings.setValue("colors/gridMajor", qcolor_to_rgba(self.grid_major_button.color()))
        self._settings.setValue("colors/gridMinor", qcolor_to_rgba(self.grid_minor_button.color()))

        # 3D View colors
        self._settings.setValue("colors/background3d", qcolor_to_rgba(self.bg_3d_button.color()))
        self._settings.setValue("colors/grid3dEnabled", self.grid_3d_enabled.isChecked())
        self._settings.setValue("colors/grid3dColor", qcolor_to_rgba(self.grid_3d_color_button.color()))
        self._settings.setValue("viewport/axis3dEnabled", self.axis_3d_enabled.isChecked())
        self._settings.setValue("viewport/axis3dThickness", self.axis_3d_thickness.value())

        # Selection colors
        self._settings.setValue("colors/selection", qcolor_to_rgba(self.selection_button.color()))
        self._settings.setValue("colors/brushOutline", qcolor_to_rgba(self.brush_outline_button.color()))
        self._settings.setValue("colors/vaoColor", qcolor_to_rgba(self.vao_color_button.color()))

        # Editor colors
        self._settings.setValue("colors/console", qcolor_to_rgba(self.console_color_button.color()))

        # 2D Brush Colors
        self._settings.setValue("colors/brush2d/structural", qcolor_to_rgb(self.brush_structural_button.color()))
        self._settings.setValue("colors/brush2d/detail", qcolor_to_rgb(self.brush_detail_button.color()))
        self._settings.setValue("colors/brush2d/weaponClip", qcolor_to_rgb(self.brush_weapon_clip_button.color()))
        self._settings.setValue("colors/brush2d/nonColliding", qcolor_to_rgb(self.brush_non_colliding_button.color()))
        self._settings.setValue("colors/brush2d/curves", qcolor_to_rgb(self.brush_curves_button.color()))
        self._settings.setValue("colors/brush2d/terrain", qcolor_to_rgb(self.brush_terrain_button.color()))

        # Shader tab - 3D View Rendering
        self._settings.setValue("render/faceCulling", self.face_culling_check.isChecked())
        self._settings.setValue("render/solidDepthTest", self.solid_depth_test_check.isChecked())

        # Wireframe settings
        self._settings.setValue("render/wireframeOverlay", self.wireframe_overlay_check.isChecked())
        self._settings.setValue("render/wireframeBackfaceCulling", self.backface_culling_3d_check.isChecked())
        self._settings.setValue("render/wireframeDepthTest", self.wireframe_depth_test_check.isChecked())
        self._settings.setValue("render/wireframeThickness", self.wireframe_thickness_spin.value())

        # 2D View
        self._settings.setValue("render/backfaceCulling2d", self.backface_culling_2d_check.isChecked())

        # Entity Display
        self._settings.setValue("render/entityMarkers", self.entity_markers_check.isChecked())
        self._settings.setValue("render/entityMarkerSize", self.entity_marker_size_spin.value())

        # Performance Optimizations
        self._settings.setValue("performance/frustumCulling", self.frustum_culling_check.isChecked())
        self._settings.setValue("performance/batchedRendering", self.batched_rendering_check.isChecked())
        self._settings.setValue("performance/octreePicking", self.octree_picking_check.isChecked())

    def _reset_to_defaults(self) -> None:
        """Reset all settings to default values."""
        # General tab - Editor
        index = self.grid_size_combo.findData(DEFAULT_GRID_SIZE)
        if index >= 0:
            self.grid_size_combo.setCurrentIndex(index)
        self.undo_levels_spin.setValue(100)
        self.load_last_map_check.setChecked(False)

        # General tab - Paths
        self.game_path_edit.clear()
        self.texture_path_edit.clear()
        self.xmodel_path_edit.clear()

        # General tab - Auto-Save
        self.autosave_enabled_check.setChecked(False)
        self.autosave_interval_spin.setValue(5)
        self.recent_files_spin.setValue(10)

        # General tab - Transformations
        self.rotation_angle_spin.setValue(15.0)
        self.scale_factor_spin.setValue(1.1)
        self.clone_offset_x_spin.setValue(16)
        self.clone_offset_y_spin.setValue(16)
        self.clone_offset_z_spin.setValue(0)

        # Viewport tab - 3D Camera
        self.fov_spin.setValue(DEFAULT_FOV)
        self.near_plane_spin.setValue(DEFAULT_NEAR_PLANE)
        self.far_plane_spin.setValue(DEFAULT_FAR_PLANE)
        self.camera_speed_spin.setValue(DEFAULT_CAMERA_SPEED)
        self.mouse_sensitivity_spin.setValue(DEFAULT_MOUSE_SENSITIVITY)
        self.zoom_speed_3d_spin.setValue(1.0)
        self.invert_mouse_y_check.setChecked(False)
        self.invert_mouse_x_check.setChecked(False)
        self.show_axis_3d_check.setChecked(True)

        # Viewport tab - 2D View
        self.default_view_combo.setCurrentIndex(0)
        self.zoom_speed_2d_spin.setValue(1.0)
        self.pan_speed_spin.setValue(1.0)
        self.show_grid_check.setChecked(True)
        self.show_axis_labels_check.setChecked(True)
        self.snap_to_grid_check.setChecked(True)
        self.show_axis_2d_check.setChecked(True)

        # Colors tab
        self.theme_combo.setCurrentIndex(0)  # Dark

        # 2D View
        self.bg_2d_button.setColor(rgba_to_qcolor(COLORS["background_2d"]))
        self.grid_major_button.setColor(rgba_to_qcolor(COLORS["grid_major"]))
        self.grid_minor_button.setColor(rgba_to_qcolor(COLORS["grid_minor"]))

        # 3D View
        self.bg_3d_button.setColor(rgba_to_qcolor(COLORS["background_3d"]))
        self.grid_3d_enabled.setChecked(True)
        self.grid_3d_color_button.setColor(rgba_to_qcolor(COLORS["grid_major"]))
        self.axis_3d_enabled.setChecked(True)
        self.axis_3d_thickness.setValue(2.0)

        # Selection
        self.selection_button.setColor(rgba_to_qcolor(COLORS["selection"]))
        self.brush_outline_button.setColor(rgba_to_qcolor(COLORS["brush_outline"]))
        self.vao_color_button.setColor(rgba_to_qcolor((0.6, 0.6, 0.6, 1.0)))

        # Editor
        self.console_color_button.setColor(rgba_to_qcolor((0.12, 0.12, 0.12, 1.0)))

        # 2D Brush Colors
        self.brush_structural_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["structural"]))
        self.brush_detail_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["detail"]))
        self.brush_weapon_clip_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["weapon_clip"]))
        self.brush_non_colliding_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["non_colliding"]))
        self.brush_curves_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["curves"]))
        self.brush_terrain_button.setColor(rgb_to_qcolor(BRUSH_COLORS_2D["terrain"]))

        # Shader tab - 3D View Rendering
        self.face_culling_check.setChecked(True)
        self.solid_depth_test_check.setChecked(True)

        # Wireframe
        self.wireframe_overlay_check.setChecked(True)
        self.backface_culling_3d_check.setChecked(True)
        self.wireframe_depth_test_check.setChecked(True)
        self.wireframe_thickness_spin.setValue(1.0)

        # 2D View
        self.backface_culling_2d_check.setChecked(True)

        # Entity Display
        self.entity_markers_check.setChecked(True)
        self.entity_marker_size_spin.setValue(16.0)

        # Performance Optimizations
        self.frustum_culling_check.setChecked(True)
        self.batched_rendering_check.setChecked(True)
        self.octree_picking_check.setChecked(True)

    def _on_ok(self) -> None:
        """Handle OK button click."""
        self._save_settings()
        self.settings_changed.emit()
        self.accept()

    def _on_apply(self) -> None:
        """Handle Apply button click."""
        self._save_settings()
        self.settings_changed.emit()

    def get_setting(self, key: str, default=None):
        """Get a setting value."""
        return self._settings.value(key, default)
