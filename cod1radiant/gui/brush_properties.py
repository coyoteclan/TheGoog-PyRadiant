"""Brush properties panel for editing selected brush dimensions."""

from __future__ import annotations

from typing import TYPE_CHECKING
import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QGroupBox,
    QFormLayout,
    QPushButton,
)
from PyQt6.QtGui import QDoubleValidator

if TYPE_CHECKING:
    from ..core import MapDocument

# Import Brush class for isinstance checks and Vec3 for coordinate conversion
from ..core import Brush as _Brush, Vec3


# Content flags for CoD1 MAP format
CONTENT_FLAGS = {
    "Structural": 0,
    "Detail": 134217728,
    "Non Colliding": 134217732,
    "Weapon Clip": 134226048,
}


class BrushPropertiesPanel(QWidget):
    """Panel for editing brush position and size."""

    # Signal emitted when brush properties change
    properties_changed = pyqtSignal()

    def __init__(self, document: "MapDocument", parent=None):
        super().__init__(parent)
        self.document = document
        self._updating = False  # Prevent recursive updates

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title = QLabel("Brush Properties")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Info label
        self.info_label = QLabel("No selection")
        self.info_label.setEnabled(False)  # Use disabled text color for secondary text
        layout.addWidget(self.info_label)

        # Position and Size in horizontal layout
        pos_size_layout = QHBoxLayout()
        pos_size_layout.setSpacing(10)

        # Position group
        pos_group = QGroupBox("Position")
        pos_layout = QFormLayout(pos_group)
        pos_layout.setSpacing(3)
        pos_layout.setContentsMargins(5, 10, 5, 5)

        self.pos_x = self._create_spinbox()
        self.pos_y = self._create_spinbox()
        self.pos_z = self._create_spinbox()

        pos_layout.addRow("X:", self.pos_x)
        pos_layout.addRow("Y:", self.pos_y)
        pos_layout.addRow("Z:", self.pos_z)

        pos_size_layout.addWidget(pos_group)

        # Size group
        size_group = QGroupBox("Size")
        size_layout = QFormLayout(size_group)
        size_layout.setSpacing(3)
        size_layout.setContentsMargins(5, 10, 5, 5)

        self.size_x = self._create_spinbox()
        self.size_y = self._create_spinbox()
        self.size_z = self._create_spinbox()

        size_layout.addRow("X:", self.size_x)
        size_layout.addRow("Y:", self.size_y)
        size_layout.addRow("Z:", self.size_z)

        pos_size_layout.addWidget(size_group)

        layout.addLayout(pos_size_layout)

        # Content Flags group with Quick Apply buttons (2 per row)
        flags_group = QGroupBox("Content Flags")
        flags_layout = QVBoxLayout(flags_group)
        flags_layout.setSpacing(3)
        flags_layout.setContentsMargins(5, 10, 5, 5)

        # Create rows with 2 buttons each
        flag_items = list(CONTENT_FLAGS.items())
        for i in range(0, len(flag_items), 2):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(3)

            # First button
            name1, value1 = flag_items[i]
            btn1 = QPushButton(name1)
            btn1.clicked.connect(lambda checked, v=value1: self._apply_content_flag(v))
            row_layout.addWidget(btn1)

            # Second button (if exists)
            if i + 1 < len(flag_items):
                name2, value2 = flag_items[i + 1]
                btn2 = QPushButton(name2)
                btn2.clicked.connect(lambda checked, v=value2: self._apply_content_flag(v))
                row_layout.addWidget(btn2)

            flags_layout.addWidget(row_widget)

        layout.addWidget(flags_group)

        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)

        layout.addStretch()

        # Connect signals
        self.pos_x.editingFinished.connect(self._on_position_changed)
        self.pos_y.editingFinished.connect(self._on_position_changed)
        self.pos_z.editingFinished.connect(self._on_position_changed)
        self.size_x.editingFinished.connect(self._on_size_changed)
        self.size_y.editingFinished.connect(self._on_size_changed)
        self.size_z.editingFinished.connect(self._on_size_changed)

    def _create_spinbox(self) -> QLineEdit:
        """Create a numeric input field."""
        edit = QLineEdit()
        edit.setValidator(QDoubleValidator(-99999, 99999, 2))
        edit.setText("0")
        edit.setMaximumWidth(80)
        return edit

    def update_from_selection(self):
        """Update panel from current selection."""
        self._updating = True

        brushes = self.document.get_selected_brushes()

        if not brushes:
            self.info_label.setText("No selection")
            self._set_enabled(False)
            self._updating = False
            return

        if len(brushes) == 1:
            brush = brushes[0]
            # Get the brush key from selection
            selected_keys = list(self.document.selection.selected_brushes)
            if selected_keys:
                entity_idx, brush_idx = selected_keys[0]
                self.info_label.setText(f"Brush ({entity_idx}, {brush_idx})")
            else:
                self.info_label.setText("Brush")

            # Get bounds using brush methods (returns Vec3)
            min_pt, max_pt = brush.get_bounding_box()
            center = brush.get_center()
            size_x = max_pt.x - min_pt.x
            size_y = max_pt.y - min_pt.y
            size_z = max_pt.z - min_pt.z

            # Update fields
            self.pos_x.setText(f"{center.x:.1f}")
            self.pos_y.setText(f"{center.y:.1f}")
            self.pos_z.setText(f"{center.z:.1f}")

            self.size_x.setText(f"{size_x:.1f}")
            self.size_y.setText(f"{size_y:.1f}")
            self.size_z.setText(f"{size_z:.1f}")

            self._set_enabled(True)
        else:
            self.info_label.setText(f"{len(brushes)} brushes selected")

            # Calculate combined bounds
            all_min = None
            all_max = None
            for brush in brushes:
                b_min, b_max = brush.get_bounding_box()
                if all_min is None:
                    all_min = np.array([b_min.x, b_min.y, b_min.z], dtype=np.float64)
                    all_max = np.array([b_max.x, b_max.y, b_max.z], dtype=np.float64)
                else:
                    all_min = np.minimum(all_min, [b_min.x, b_min.y, b_min.z])
                    all_max = np.maximum(all_max, [b_max.x, b_max.y, b_max.z])

            center = (all_min + all_max) / 2
            size = all_max - all_min

            self.pos_x.setText(f"{center[0]:.1f}")
            self.pos_y.setText(f"{center[1]:.1f}")
            self.pos_z.setText(f"{center[2]:.1f}")

            self.size_x.setText(f"{size[0]:.1f}")
            self.size_y.setText(f"{size[1]:.1f}")
            self.size_z.setText(f"{size[2]:.1f}")

            self._set_enabled(True)

        self._updating = False

    def _set_enabled(self, enabled: bool):
        """Enable or disable input fields."""
        self.pos_x.setEnabled(enabled)
        self.pos_y.setEnabled(enabled)
        self.pos_z.setEnabled(enabled)
        self.size_x.setEnabled(enabled)
        self.size_y.setEnabled(enabled)
        self.size_z.setEnabled(enabled)

    def _on_position_changed(self):
        """Handle position field change."""
        if self._updating:
            return
        self._apply_changes()

    def _on_size_changed(self):
        """Handle size field change."""
        if self._updating:
            return
        self._apply_changes()

    def _on_apply(self):
        """Apply button clicked."""
        self._apply_changes()

    def _apply_content_flag(self, flag_value: int):
        """Apply a content flag to all faces of selected brushes."""
        brushes = self.document.get_selected_brushes()
        if not brushes:
            return

        for brush in brushes:
            # Only apply to actual brushes, not patches
            if isinstance(brush, _Brush):
                for plane in brush.planes:
                    plane.content_flags = flag_value

        self.document.modified = True
        self.properties_changed.emit()

    def _apply_changes(self):
        """Apply the current values to selected brushes."""
        brushes = self.document.get_selected_brushes()
        if not brushes:
            return

        try:
            new_pos = np.array([
                float(self.pos_x.text()),
                float(self.pos_y.text()),
                float(self.pos_z.text()),
            ], dtype=np.float64)

            new_size = np.array([
                float(self.size_x.text()),
                float(self.size_y.text()),
                float(self.size_z.text()),
            ], dtype=np.float64)
        except ValueError:
            return  # Invalid input

        # Ensure minimum size
        new_size = np.maximum(new_size, np.array([1.0, 1.0, 1.0]))

        if len(brushes) == 1:
            brush = brushes[0]

            # Current state
            old_center = brush.get_center()
            old_min, old_max = brush.get_bounding_box()
            old_size = np.array([old_max.x - old_min.x, old_max.y - old_min.y, old_max.z - old_min.z])

            # Calculate scale factor (use uniform scaling with average)
            scale_factors = new_size / np.maximum(old_size, np.array([0.001, 0.001, 0.001]))
            avg_scale = np.mean(scale_factors)

            # Scale brush around its center (uniform scale only)
            if abs(avg_scale - 1.0) > 0.001:
                brush.scale(avg_scale, old_center)

            # Move to new position
            new_center = brush.get_center()
            offset = Vec3(new_pos[0] - new_center.x, new_pos[1] - new_center.y, new_pos[2] - new_center.z)
            if abs(offset.x) > 0.001 or abs(offset.y) > 0.001 or abs(offset.z) > 0.001:
                brush.translate(offset)

        else:
            # Multiple brushes - move as group
            all_min = None
            all_max = None
            for brush in brushes:
                b_min, b_max = brush.get_bounding_box()
                if all_min is None:
                    all_min = np.array([b_min.x, b_min.y, b_min.z], dtype=np.float64)
                    all_max = np.array([b_max.x, b_max.y, b_max.z], dtype=np.float64)
                else:
                    all_min = np.minimum(all_min, [b_min.x, b_min.y, b_min.z])
                    all_max = np.maximum(all_max, [b_max.x, b_max.y, b_max.z])

            old_center_arr = (all_min + all_max) / 2
            old_center = Vec3(old_center_arr[0], old_center_arr[1], old_center_arr[2])
            old_size = all_max - all_min

            # Scale all brushes around group center (uniform scale)
            scale_factors = new_size / np.maximum(old_size, np.array([0.001, 0.001, 0.001]))
            avg_scale = np.mean(scale_factors)
            if abs(avg_scale - 1.0) > 0.001:
                for brush in brushes:
                    brush.scale(avg_scale, old_center)

            # Recalculate center after scaling
            all_min = None
            all_max = None
            for brush in brushes:
                b_min, b_max = brush.get_bounding_box()
                if all_min is None:
                    all_min = np.array([b_min.x, b_min.y, b_min.z], dtype=np.float64)
                    all_max = np.array([b_max.x, b_max.y, b_max.z], dtype=np.float64)
                else:
                    all_min = np.minimum(all_min, [b_min.x, b_min.y, b_min.z])
                    all_max = np.maximum(all_max, [b_max.x, b_max.y, b_max.z])

            new_group_center = (all_min + all_max) / 2

            # Move all brushes
            offset_arr = new_pos - new_group_center
            if np.linalg.norm(offset_arr) > 0.001:
                offset = Vec3(offset_arr[0], offset_arr[1], offset_arr[2])
                for brush in brushes:
                    brush.translate(offset)

        self.document.modified = True
        self.properties_changed.emit()

    def set_document(self, document: "MapDocument"):
        """Set the document."""
        self.document = document
        self.update_from_selection()
