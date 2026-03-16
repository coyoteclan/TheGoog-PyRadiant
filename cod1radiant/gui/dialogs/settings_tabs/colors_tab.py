"""Colors settings tab for the settings dialog."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
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
    QLineEdit,
    QPushButton,
    QFileDialog,
)

from ....config import (
    COLORS,
    THEMES,
    BRUSH_COLORS_2D,
    THEME_NAMES,
    UI_DENSITY_NAMES,
)
from .color_utils import ColorButton, rgba_to_qcolor, rgb_to_qcolor


class ColorsTab(QWidget):
    """Colors settings tab with Editor, 2D View, 3D View, Selection, and Brush Colors groups."""

    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        main_layout = QVBoxLayout(self)

        # Editor Theme group (full width at top)
        main_layout.addWidget(self._create_editor_group())

        # Row 1: 2D View | 3D View side by side
        row1 = QHBoxLayout()
        row1.addWidget(self._create_2d_view_group())
        row1.addWidget(self._create_3d_view_group())
        main_layout.addLayout(row1)

        # Row 2: Selection | 2D Brush Colors side by side
        row2 = QHBoxLayout()
        row2.addWidget(self._create_selection_group())
        row2.addWidget(self._create_brush_colors_group())
        main_layout.addLayout(row2)

        main_layout.addStretch()

    def _create_editor_group(self) -> QGroupBox:
        """Create the Editor settings group."""
        group = QGroupBox("Editor")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(15)
        grid.setVerticalSpacing(8)

        # Theme dropdown with all built-in themes
        grid.addWidget(QLabel("Theme:"), 0, 0)
        self.theme_combo = QComboBox()
        for theme_key, theme_name in THEME_NAMES.items():
            self.theme_combo.addItem(theme_name, theme_key)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.theme_combo.setFixedWidth(120)
        grid.addWidget(self.theme_combo, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # UI Density dropdown
        grid.addWidget(QLabel("UI Density:"), 0, 2)
        self.density_combo = QComboBox()
        for density_key, density_name in UI_DENSITY_NAMES.items():
            self.density_combo.addItem(density_name, density_key)
        self.density_combo.setFixedWidth(100)
        self.density_combo.setToolTip("Compact mode reduces padding and spacing for smaller screens")
        grid.addWidget(self.density_combo, 0, 3, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Console Color:"), 0, 4)
        self.console_color_button = ColorButton(QColor(30, 30, 30))
        grid.addWidget(self.console_color_button, 0, 5, Qt.AlignmentFlag.AlignLeft)

        # Custom stylesheet row
        grid.addWidget(QLabel("Custom Stylesheet:"), 1, 0)
        self.custom_stylesheet_edit = QLineEdit()
        self.custom_stylesheet_edit.setPlaceholderText("Path to custom .qss file...")
        self.custom_stylesheet_edit.setEnabled(False)
        grid.addWidget(self.custom_stylesheet_edit, 1, 1, 1, 2)
        self.custom_stylesheet_browse = QPushButton("...")
        self.custom_stylesheet_browse.setFixedWidth(30)
        self.custom_stylesheet_browse.setEnabled(False)
        self.custom_stylesheet_browse.clicked.connect(self._browse_custom_stylesheet)
        grid.addWidget(self.custom_stylesheet_browse, 1, 3, Qt.AlignmentFlag.AlignLeft)

        grid.setColumnStretch(6, 1)
        return group

    def _create_2d_view_group(self) -> QGroupBox:
        """Create the 2D View colors group."""
        group = QGroupBox("2D View")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Viewport Color:"), 0, 0)
        self.bg_2d_button = ColorButton(rgba_to_qcolor(COLORS["background_2d"]))
        grid.addWidget(self.bg_2d_button, 0, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Major Lines:"), 1, 0)
        self.grid_major_button = ColorButton(rgba_to_qcolor(COLORS["grid_major"]))
        grid.addWidget(self.grid_major_button, 1, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Minor Lines:"), 2, 0)
        self.grid_minor_button = ColorButton(rgba_to_qcolor(COLORS["grid_minor"]))
        grid.addWidget(self.grid_minor_button, 2, 1, Qt.AlignmentFlag.AlignLeft)

        grid.setRowStretch(3, 1)
        return group

    def _create_3d_view_group(self) -> QGroupBox:
        """Create the 3D View colors group."""
        group = QGroupBox("3D View")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Viewport Color:"), 0, 0)
        self.bg_3d_button = ColorButton(rgba_to_qcolor(COLORS["background_3d"]))
        grid.addWidget(self.bg_3d_button, 0, 1, Qt.AlignmentFlag.AlignLeft)

        # Grid row
        self.grid_3d_enabled = QCheckBox("Show Grid")
        self.grid_3d_enabled.setChecked(True)
        grid.addWidget(self.grid_3d_enabled, 1, 0)
        self.grid_3d_color_button = ColorButton(rgba_to_qcolor(COLORS["grid_major"]))
        grid.addWidget(self.grid_3d_color_button, 1, 1, Qt.AlignmentFlag.AlignLeft)

        # Axis row
        axis_container = QWidget()
        axis_layout = QHBoxLayout(axis_container)
        axis_layout.setContentsMargins(0, 0, 0, 0)
        axis_layout.setSpacing(5)
        self.axis_3d_enabled = QCheckBox("Show Axis")
        self.axis_3d_enabled.setChecked(True)
        axis_layout.addWidget(self.axis_3d_enabled)
        axis_layout.addWidget(QLabel("Thickness:"))
        self.axis_3d_thickness = QDoubleSpinBox()
        self.axis_3d_thickness.setRange(1.0, 10.0)
        self.axis_3d_thickness.setValue(2.0)
        self.axis_3d_thickness.setSingleStep(0.5)
        self.axis_3d_thickness.setDecimals(1)
        self.axis_3d_thickness.setFixedWidth(55)
        axis_layout.addWidget(self.axis_3d_thickness)
        axis_layout.addStretch()
        grid.addWidget(axis_container, 2, 0, 1, 2)

        grid.setRowStretch(3, 1)
        return group

    def _create_selection_group(self) -> QGroupBox:
        """Create the Selection colors group."""
        group = QGroupBox("Selection")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Selection Color:"), 0, 0)
        self.selection_button = ColorButton(rgba_to_qcolor(COLORS["selection"]))
        grid.addWidget(self.selection_button, 0, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Brush Outline:"), 1, 0)
        self.brush_outline_button = ColorButton(rgba_to_qcolor(COLORS["brush_outline"]))
        grid.addWidget(self.brush_outline_button, 1, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Brush Fill (3D):"), 2, 0)
        self.vao_color_button = ColorButton(QColor(153, 153, 153))
        grid.addWidget(self.vao_color_button, 2, 1, Qt.AlignmentFlag.AlignLeft)

        grid.setRowStretch(3, 1)
        return group

    def _create_brush_colors_group(self) -> QGroupBox:
        """Create the 2D Brush Colors group."""
        group = QGroupBox("2D Brush Colors")
        grid = QGridLayout(group)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        # Column 1
        grid.addWidget(QLabel("Structural:"), 0, 0)
        self.brush_structural_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["structural"]))
        grid.addWidget(self.brush_structural_button, 0, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Detail:"), 1, 0)
        self.brush_detail_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["detail"]))
        grid.addWidget(self.brush_detail_button, 1, 1, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Weapon Clip:"), 2, 0)
        self.brush_weapon_clip_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["weapon_clip"]))
        grid.addWidget(self.brush_weapon_clip_button, 2, 1, Qt.AlignmentFlag.AlignLeft)

        # Column 2
        grid.addWidget(QLabel("Non-Colliding:"), 0, 2)
        self.brush_non_colliding_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["non_colliding"]))
        grid.addWidget(self.brush_non_colliding_button, 0, 3, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Curves:"), 1, 2)
        self.brush_curves_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["curves"]))
        grid.addWidget(self.brush_curves_button, 1, 3, Qt.AlignmentFlag.AlignLeft)

        grid.addWidget(QLabel("Terrain:"), 2, 2)
        self.brush_terrain_button = ColorButton(rgb_to_qcolor(BRUSH_COLORS_2D["terrain"]))
        grid.addWidget(self.brush_terrain_button, 2, 3, Qt.AlignmentFlag.AlignLeft)

        grid.setRowStretch(3, 1)
        return group

    def _on_theme_changed(self, index: int) -> None:
        """Handle theme selection change - apply theme colors."""
        theme_name = self.theme_combo.currentData()

        # Enable/disable custom stylesheet controls
        is_custom = (theme_name == "custom")
        self.custom_stylesheet_edit.setEnabled(is_custom)
        self.custom_stylesheet_browse.setEnabled(is_custom)

        # Get theme colors (use dark colors as fallback for custom/unknown themes)
        theme_colors = THEMES.get(theme_name, COLORS)

        # Update all color buttons with theme colors
        self.bg_2d_button.setColor(rgba_to_qcolor(theme_colors["background_2d"]))
        self.grid_major_button.setColor(rgba_to_qcolor(theme_colors["grid_major"]))
        self.grid_minor_button.setColor(rgba_to_qcolor(theme_colors["grid_minor"]))
        self.bg_3d_button.setColor(rgba_to_qcolor(theme_colors["background_3d"]))
        self.grid_3d_color_button.setColor(rgba_to_qcolor(theme_colors["grid_major"]))
        self.selection_button.setColor(rgba_to_qcolor(theme_colors["selection"]))
        self.brush_outline_button.setColor(rgba_to_qcolor(theme_colors["brush_outline"]))
        self.vao_color_button.setColor(rgba_to_qcolor(theme_colors.get("vao_color", (0.6, 0.6, 0.6, 1.0))))
        self.console_color_button.setColor(rgba_to_qcolor(theme_colors.get("console", (0.12, 0.12, 0.12, 1.0))))

        # Emit signal for parent dialog
        self.theme_changed.emit(theme_name)

    def _browse_custom_stylesheet(self) -> None:
        """Browse for a custom .qss stylesheet file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Stylesheet",
            "",
            "Qt Stylesheet Files (*.qss);;All Files (*.*)"
        )
        if file_path:
            self.custom_stylesheet_edit.setText(file_path)
