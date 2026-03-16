"""Shader/Rendering settings tab for the settings dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QCheckBox,
)


class ShaderTab(QWidget):
    """Shader/Rendering settings tab with 3D/2D rendering options and performance settings."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        main_layout = QVBoxLayout(self)

        # Row 1: 3D View Rendering | 2D View Rendering side by side
        row1 = QHBoxLayout()
        row1.addWidget(self._create_3d_rendering_group())
        row1.addWidget(self._create_2d_rendering_group())
        main_layout.addLayout(row1)

        # Row 2: Wireframe Overlay | Entity Display side by side
        row2 = QHBoxLayout()
        row2.addWidget(self._create_wireframe_group())
        row2.addWidget(self._create_entity_group())
        main_layout.addLayout(row2)

        # Performance Optimizations group (full width at bottom)
        main_layout.addWidget(self._create_performance_group())

        main_layout.addStretch()

    def _create_3d_rendering_group(self) -> QGroupBox:
        """Create the 3D View Rendering group."""
        group = QGroupBox("3D View Rendering")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.face_culling_check = QCheckBox("Face Culling")
        self.face_culling_check.setChecked(True)
        self.face_culling_check.setToolTip("Cull back-facing polygons for solid brush rendering")
        grid.addWidget(self.face_culling_check, 0, 0)

        self.solid_depth_test_check = QCheckBox("Depth Test")
        self.solid_depth_test_check.setChecked(True)
        self.solid_depth_test_check.setToolTip("Enable depth testing for solid brush rendering")
        grid.addWidget(self.solid_depth_test_check, 1, 0)

        grid.setRowStretch(2, 1)
        return group

    def _create_2d_rendering_group(self) -> QGroupBox:
        """Create the 2D View Rendering group."""
        group = QGroupBox("2D View Rendering")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.backface_culling_2d_check = QCheckBox("Backface Culling")
        self.backface_culling_2d_check.setChecked(True)
        self.backface_culling_2d_check.setToolTip("Only show edges of faces visible from the current view direction")
        grid.addWidget(self.backface_culling_2d_check, 0, 0)

        grid.setRowStretch(1, 1)
        return group

    def _create_wireframe_group(self) -> QGroupBox:
        """Create the Wireframe Overlay group."""
        group = QGroupBox("Wireframe Overlay (3D)")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.wireframe_overlay_check = QCheckBox("Show Wireframe")
        self.wireframe_overlay_check.setChecked(True)
        self.wireframe_overlay_check.setToolTip("Show wireframe overlay on brushes (Toggle: F)")
        grid.addWidget(self.wireframe_overlay_check, 0, 0)

        self.backface_culling_3d_check = QCheckBox("Backface Culling")
        self.backface_culling_3d_check.setChecked(True)
        self.backface_culling_3d_check.setToolTip("Hide edges of faces that point away from the camera")
        grid.addWidget(self.backface_culling_3d_check, 1, 0)

        self.wireframe_depth_test_check = QCheckBox("Depth Test")
        self.wireframe_depth_test_check.setChecked(True)
        self.wireframe_depth_test_check.setToolTip("Hide wireframes that are behind other objects")
        grid.addWidget(self.wireframe_depth_test_check, 2, 0)

        # Line Thickness
        thickness_container = QWidget()
        thickness_layout = QHBoxLayout(thickness_container)
        thickness_layout.setContentsMargins(0, 0, 0, 0)
        thickness_layout.setSpacing(5)
        thickness_layout.addWidget(QLabel("Line Thickness:"))
        self.wireframe_thickness_spin = QDoubleSpinBox()
        self.wireframe_thickness_spin.setRange(0.5, 5.0)
        self.wireframe_thickness_spin.setSingleStep(0.5)
        self.wireframe_thickness_spin.setValue(1.0)
        self.wireframe_thickness_spin.setToolTip("Line thickness for wireframe rendering")
        self.wireframe_thickness_spin.setFixedWidth(60)
        thickness_layout.addWidget(self.wireframe_thickness_spin)
        thickness_layout.addStretch()
        grid.addWidget(thickness_container, 3, 0)

        grid.setRowStretch(4, 1)
        return group

    def _create_entity_group(self) -> QGroupBox:
        """Create the Entity Display group."""
        group = QGroupBox("Entity Display (3D)")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        self.entity_markers_check = QCheckBox("Show Entity Markers")
        self.entity_markers_check.setChecked(True)
        self.entity_markers_check.setToolTip(
            "Show point entity markers in 3D view (Toggle: M)\n"
            "Lights, spawn points, and other point entities."
        )
        grid.addWidget(self.entity_markers_check, 0, 0)

        # Marker Size
        marker_container = QWidget()
        marker_layout = QHBoxLayout(marker_container)
        marker_layout.setContentsMargins(0, 0, 0, 0)
        marker_layout.setSpacing(5)
        marker_layout.addWidget(QLabel("Marker Size:"))
        self.entity_marker_size_spin = QDoubleSpinBox()
        self.entity_marker_size_spin.setRange(4.0, 64.0)
        self.entity_marker_size_spin.setSingleStep(4.0)
        self.entity_marker_size_spin.setValue(16.0)
        self.entity_marker_size_spin.setToolTip("Size of entity markers in world units")
        self.entity_marker_size_spin.setFixedWidth(60)
        marker_layout.addWidget(self.entity_marker_size_spin)
        marker_layout.addStretch()
        grid.addWidget(marker_container, 1, 0)

        grid.setRowStretch(2, 1)
        return group

    def _create_performance_group(self) -> QGroupBox:
        """Create the Performance Optimizations group."""
        group = QGroupBox("Performance Optimizations")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(8)

        self.frustum_culling_check = QCheckBox("Frustum Culling")
        self.frustum_culling_check.setChecked(True)
        self.frustum_culling_check.setToolTip(
            "Skip rendering brushes outside the camera view (Toggle: C)\n"
            "Improves performance on large maps."
        )
        grid.addWidget(self.frustum_culling_check, 0, 0)

        self.batched_rendering_check = QCheckBox("Batched Rendering")
        self.batched_rendering_check.setChecked(True)
        self.batched_rendering_check.setToolTip(
            "Combine brushes into single draw calls (Toggle: B)\n"
            "Reduces GPU overhead from N to 4 draw calls."
        )
        grid.addWidget(self.batched_rendering_check, 0, 1)

        self.octree_picking_check = QCheckBox("Octree Picking")
        self.octree_picking_check.setChecked(True)
        self.octree_picking_check.setToolTip(
            "Use spatial octree for brush picking (Toggle: O)\n"
            "Reduces picking time from O(n) to O(log n)."
        )
        grid.addWidget(self.octree_picking_check, 0, 2)

        grid.setColumnStretch(3, 1)
        return group
