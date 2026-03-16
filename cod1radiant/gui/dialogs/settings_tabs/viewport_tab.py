"""Viewport settings tab for the settings dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
)

from ....config import (
    DEFAULT_NEAR_PLANE,
    DEFAULT_FAR_PLANE,
    DEFAULT_FOV,
    DEFAULT_CAMERA_SPEED,
    DEFAULT_MOUSE_SENSITIVITY,
)


class ViewportTab(QWidget):
    """Viewport settings tab with 3D Camera and 2D View groups."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        main_layout = QVBoxLayout(self)

        # Row 1: 3D Camera | 2D View side by side
        row1 = QHBoxLayout()
        row1.addWidget(self._create_camera_group())
        row1.addWidget(self._create_2d_view_group())
        main_layout.addLayout(row1)

        main_layout.addStretch()

    def _create_camera_group(self) -> QGroupBox:
        """Create the 3D Camera settings group."""
        group = QGroupBox("3D Camera")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Field of View
        grid.addWidget(QLabel("Field of View:"), 0, 0)
        self.fov_spin = QDoubleSpinBox()
        self.fov_spin.setRange(30.0, 150.0)
        self.fov_spin.setValue(DEFAULT_FOV)
        self.fov_spin.setSuffix("°")
        self.fov_spin.setFixedWidth(80)
        grid.addWidget(self.fov_spin, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # Near Clip
        grid.addWidget(QLabel("Near Clip:"), 1, 0)
        self.near_plane_spin = QDoubleSpinBox()
        self.near_plane_spin.setRange(0.1, 100.0)
        self.near_plane_spin.setValue(DEFAULT_NEAR_PLANE)
        self.near_plane_spin.setDecimals(1)
        self.near_plane_spin.setFixedWidth(80)
        grid.addWidget(self.near_plane_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Far Clip
        grid.addWidget(QLabel("Far Clip:"), 2, 0)
        self.far_plane_spin = QDoubleSpinBox()
        self.far_plane_spin.setRange(1000.0, 100000.0)
        self.far_plane_spin.setValue(DEFAULT_FAR_PLANE)
        self.far_plane_spin.setDecimals(0)
        self.far_plane_spin.setFixedWidth(80)
        grid.addWidget(self.far_plane_spin, 2, 1, Qt.AlignmentFlag.AlignLeft)

        # Movement Speed
        grid.addWidget(QLabel("Movement Speed:"), 3, 0)
        self.camera_speed_spin = QDoubleSpinBox()
        self.camera_speed_spin.setRange(50.0, 2000.0)
        self.camera_speed_spin.setValue(DEFAULT_CAMERA_SPEED)
        self.camera_speed_spin.setSuffix(" u/s")
        self.camera_speed_spin.setFixedWidth(100)
        grid.addWidget(self.camera_speed_spin, 3, 1, Qt.AlignmentFlag.AlignLeft)

        # Mouse Sensitivity
        grid.addWidget(QLabel("Mouse Sensitivity:"), 4, 0)
        self.mouse_sensitivity_spin = QDoubleSpinBox()
        self.mouse_sensitivity_spin.setRange(0.05, 1.0)
        self.mouse_sensitivity_spin.setValue(DEFAULT_MOUSE_SENSITIVITY)
        self.mouse_sensitivity_spin.setSingleStep(0.05)
        self.mouse_sensitivity_spin.setDecimals(2)
        self.mouse_sensitivity_spin.setFixedWidth(80)
        grid.addWidget(self.mouse_sensitivity_spin, 4, 1, Qt.AlignmentFlag.AlignLeft)

        # Zoom Speed (3D)
        grid.addWidget(QLabel("Zoom Speed:"), 5, 0)
        self.zoom_speed_3d_spin = QDoubleSpinBox()
        self.zoom_speed_3d_spin.setRange(0.1, 5.0)
        self.zoom_speed_3d_spin.setValue(1.0)
        self.zoom_speed_3d_spin.setSingleStep(0.1)
        self.zoom_speed_3d_spin.setDecimals(1)
        self.zoom_speed_3d_spin.setFixedWidth(80)
        grid.addWidget(self.zoom_speed_3d_spin, 5, 1, Qt.AlignmentFlag.AlignLeft)

        # Invert Mouse Y
        self.invert_mouse_y_check = QCheckBox("Invert Mouse Y")
        self.invert_mouse_y_check.setChecked(False)
        grid.addWidget(self.invert_mouse_y_check, 6, 0, 1, 2)

        # Invert Mouse X
        self.invert_mouse_x_check = QCheckBox("Invert Mouse X")
        self.invert_mouse_x_check.setChecked(False)
        grid.addWidget(self.invert_mouse_x_check, 7, 0, 1, 2)

        # Show Axis (3D)
        self.show_axis_3d_check = QCheckBox("Show Axis")
        self.show_axis_3d_check.setChecked(True)
        grid.addWidget(self.show_axis_3d_check, 8, 0, 1, 2)

        grid.setRowStretch(9, 1)
        return group

    def _create_2d_view_group(self) -> QGroupBox:
        """Create the 2D View settings group."""
        group = QGroupBox("2D View")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Default View
        grid.addWidget(QLabel("Default View:"), 0, 0)
        self.default_view_combo = QComboBox()
        self.default_view_combo.addItem("Top (XY)", "xy")
        self.default_view_combo.addItem("Front (XZ)", "xz")
        self.default_view_combo.addItem("Side (YZ)", "yz")
        self.default_view_combo.setFixedWidth(100)
        grid.addWidget(self.default_view_combo, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # Zoom Speed (2D)
        grid.addWidget(QLabel("Zoom Speed:"), 1, 0)
        self.zoom_speed_2d_spin = QDoubleSpinBox()
        self.zoom_speed_2d_spin.setRange(0.1, 5.0)
        self.zoom_speed_2d_spin.setValue(1.0)
        self.zoom_speed_2d_spin.setSingleStep(0.1)
        self.zoom_speed_2d_spin.setDecimals(1)
        self.zoom_speed_2d_spin.setFixedWidth(80)
        grid.addWidget(self.zoom_speed_2d_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Pan Speed
        grid.addWidget(QLabel("Pan Speed:"), 2, 0)
        self.pan_speed_spin = QDoubleSpinBox()
        self.pan_speed_spin.setRange(0.1, 5.0)
        self.pan_speed_spin.setValue(1.0)
        self.pan_speed_spin.setSingleStep(0.1)
        self.pan_speed_spin.setDecimals(1)
        self.pan_speed_spin.setFixedWidth(80)
        grid.addWidget(self.pan_speed_spin, 2, 1, Qt.AlignmentFlag.AlignLeft)

        # Show Grid
        self.show_grid_check = QCheckBox("Show Grid")
        self.show_grid_check.setChecked(True)
        grid.addWidget(self.show_grid_check, 3, 0, 1, 2)

        # Show Axis Labels
        self.show_axis_labels_check = QCheckBox("Show Axis Labels")
        self.show_axis_labels_check.setChecked(True)
        grid.addWidget(self.show_axis_labels_check, 4, 0, 1, 2)

        # Snap to Grid
        self.snap_to_grid_check = QCheckBox("Snap to Grid")
        self.snap_to_grid_check.setChecked(True)
        grid.addWidget(self.snap_to_grid_check, 5, 0, 1, 2)

        # Show Axis (2D)
        self.show_axis_2d_check = QCheckBox("Show Axis")
        self.show_axis_2d_check.setChecked(True)
        grid.addWidget(self.show_axis_2d_check, 6, 0, 1, 2)

        grid.setRowStretch(7, 1)
        return group
