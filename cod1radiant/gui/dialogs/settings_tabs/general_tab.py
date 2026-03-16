"""General settings tab for the settings dialog."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
    QComboBox,
    QPushButton,
    QFileDialog,
)

from ....config import DEFAULT_GRID_SIZE, DEFAULT_GAME_PATH, DEFAULT_TEXTURE_PATH, GRID_SIZES


class GeneralTab(QWidget):
    """General settings tab with Editor, Paths, Auto-Save, and Transformations groups."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        main_layout = QVBoxLayout(self)

        # Row 1: Editor | Paths side by side
        row1 = QHBoxLayout()
        row1.addWidget(self._create_editor_group())
        row1.addWidget(self._create_paths_group(), 1)
        main_layout.addLayout(row1)

        # Row 2: Auto-Save | Transformations side by side
        row2 = QHBoxLayout()
        row2.addWidget(self._create_autosave_group())
        row2.addWidget(self._create_transform_group())
        main_layout.addLayout(row2)

        main_layout.addStretch()

    def _create_editor_group(self) -> QGroupBox:
        """Create the Editor settings group."""
        group = QGroupBox("Editor")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Default Grid Size
        grid.addWidget(QLabel("Default Grid Size:"), 0, 0)
        self.grid_size_combo = QComboBox()
        self.grid_size_combo.setFixedWidth(80)
        for size in GRID_SIZES:
            self.grid_size_combo.addItem(str(size), size)
        grid.addWidget(self.grid_size_combo, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # Undo Levels
        grid.addWidget(QLabel("Undo Levels:"), 1, 0)
        self.undo_levels_spin = QSpinBox()
        self.undo_levels_spin.setRange(10, 500)
        self.undo_levels_spin.setValue(100)
        self.undo_levels_spin.setFixedWidth(80)
        grid.addWidget(self.undo_levels_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Load Last Map on Startup
        self.load_last_map_check = QCheckBox("Load Last Map on Startup")
        self.load_last_map_check.setChecked(False)
        grid.addWidget(self.load_last_map_check, 2, 0, 1, 2)

        grid.setRowStretch(3, 1)
        return group

    def _create_paths_group(self) -> QGroupBox:
        """Create the Paths settings group."""
        group = QGroupBox("Paths")
        grid = QGridLayout(group)
        grid.setColumnStretch(1, 1)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Game Path
        grid.addWidget(QLabel("Game Path:"), 0, 0)
        self.game_path_edit = QLineEdit()
        self.game_path_edit.setPlaceholderText(str(DEFAULT_GAME_PATH))
        grid.addWidget(self.game_path_edit, 0, 1)
        game_path_browse = QPushButton("...")
        game_path_browse.setFixedWidth(30)
        game_path_browse.clicked.connect(lambda: self._browse_path(self.game_path_edit))
        grid.addWidget(game_path_browse, 0, 2)

        # Texture Path
        grid.addWidget(QLabel("Texture Path:"), 1, 0)
        self.texture_path_edit = QLineEdit()
        self.texture_path_edit.setPlaceholderText(str(DEFAULT_TEXTURE_PATH))
        grid.addWidget(self.texture_path_edit, 1, 1)
        texture_path_browse = QPushButton("...")
        texture_path_browse.setFixedWidth(30)
        texture_path_browse.clicked.connect(lambda: self._browse_path(self.texture_path_edit))
        grid.addWidget(texture_path_browse, 1, 2)

        # XModel Path
        grid.addWidget(QLabel("XModel Path:"), 2, 0)
        self.xmodel_path_edit = QLineEdit()
        self.xmodel_path_edit.setPlaceholderText("Path to xmodel folder")
        grid.addWidget(self.xmodel_path_edit, 2, 1)
        xmodel_path_browse = QPushButton("...")
        xmodel_path_browse.setFixedWidth(30)
        xmodel_path_browse.clicked.connect(lambda: self._browse_path(self.xmodel_path_edit))
        grid.addWidget(xmodel_path_browse, 2, 2)

        grid.setRowStretch(3, 1)
        return group

    def _create_autosave_group(self) -> QGroupBox:
        """Create the Auto-Save settings group."""
        group = QGroupBox("Auto-Save")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Auto-Save Enabled
        self.autosave_enabled_check = QCheckBox("Enable Auto-Save")
        self.autosave_enabled_check.setChecked(False)
        grid.addWidget(self.autosave_enabled_check, 0, 0, 1, 2)

        # Auto-Save Interval
        grid.addWidget(QLabel("Interval:"), 1, 0)
        self.autosave_interval_spin = QSpinBox()
        self.autosave_interval_spin.setRange(1, 60)
        self.autosave_interval_spin.setValue(5)
        self.autosave_interval_spin.setSuffix(" min")
        self.autosave_interval_spin.setFixedWidth(80)
        grid.addWidget(self.autosave_interval_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Recent Files Count
        grid.addWidget(QLabel("Recent Files:"), 2, 0)
        self.recent_files_spin = QSpinBox()
        self.recent_files_spin.setRange(5, 20)
        self.recent_files_spin.setValue(10)
        self.recent_files_spin.setFixedWidth(80)
        grid.addWidget(self.recent_files_spin, 2, 1, Qt.AlignmentFlag.AlignLeft)

        grid.setRowStretch(3, 1)
        return group

    def _create_transform_group(self) -> QGroupBox:
        """Create the Transformations settings group."""
        group = QGroupBox("Transformations")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Default Rotation Angle
        grid.addWidget(QLabel("Rotation Angle:"), 0, 0)
        self.rotation_angle_spin = QDoubleSpinBox()
        self.rotation_angle_spin.setRange(1.0, 90.0)
        self.rotation_angle_spin.setValue(15.0)
        self.rotation_angle_spin.setSuffix("°")
        self.rotation_angle_spin.setFixedWidth(80)
        grid.addWidget(self.rotation_angle_spin, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # Default Scale Factor
        grid.addWidget(QLabel("Scale Factor:"), 1, 0)
        self.scale_factor_spin = QDoubleSpinBox()
        self.scale_factor_spin.setRange(0.1, 10.0)
        self.scale_factor_spin.setValue(1.1)
        self.scale_factor_spin.setSingleStep(0.1)
        self.scale_factor_spin.setDecimals(2)
        self.scale_factor_spin.setFixedWidth(80)
        grid.addWidget(self.scale_factor_spin, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Clone Offset
        grid.addWidget(QLabel("Clone Offset:"), 2, 0)
        clone_offset_container = QWidget()
        clone_offset_layout = QHBoxLayout(clone_offset_container)
        clone_offset_layout.setContentsMargins(0, 0, 0, 0)
        clone_offset_layout.setSpacing(5)

        self.clone_offset_x_spin = QSpinBox()
        self.clone_offset_x_spin.setRange(-1024, 1024)
        self.clone_offset_x_spin.setValue(16)
        self.clone_offset_x_spin.setPrefix("X: ")
        self.clone_offset_x_spin.setFixedWidth(75)
        clone_offset_layout.addWidget(self.clone_offset_x_spin)

        self.clone_offset_y_spin = QSpinBox()
        self.clone_offset_y_spin.setRange(-1024, 1024)
        self.clone_offset_y_spin.setValue(16)
        self.clone_offset_y_spin.setPrefix("Y: ")
        self.clone_offset_y_spin.setFixedWidth(75)
        clone_offset_layout.addWidget(self.clone_offset_y_spin)

        self.clone_offset_z_spin = QSpinBox()
        self.clone_offset_z_spin.setRange(-1024, 1024)
        self.clone_offset_z_spin.setValue(0)
        self.clone_offset_z_spin.setPrefix("Z: ")
        self.clone_offset_z_spin.setFixedWidth(75)
        clone_offset_layout.addWidget(self.clone_offset_z_spin)

        clone_offset_layout.addStretch()
        grid.addWidget(clone_offset_container, 2, 1)

        grid.setRowStretch(3, 1)
        return group

    def _browse_path(self, line_edit: QLineEdit) -> None:
        """Open a directory browser dialog."""
        path = QFileDialog.getExistingDirectory(
            self,
            "Select Directory",
            line_edit.text() or str(Path.home())
        )
        if path:
            line_edit.setText(path)
