"""Texture properties panel for editing face textures."""

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
    QSpinBox,
    QDoubleSpinBox,
)
from PyQt6.QtGui import QDoubleValidator

if TYPE_CHECKING:
    from ..core import MapDocument
    from .main_window import MainWindow

# Import Brush and BrushPlane classes for isinstance checks
from ..core import Brush as _Brush, BrushPlane


class TexturePropertiesPanel(QWidget):
    """Panel for editing texture properties of selected faces/brushes."""

    # Signal emitted when texture properties change
    properties_changed = pyqtSignal()

    # Signal emitted when browse button is clicked
    browse_requested = pyqtSignal()

    def __init__(self, document: "MapDocument", parent=None):
        super().__init__(parent)
        self.document = document
        self._updating = False  # Prevent recursive updates
        self._selected_faces: list[BrushPlane] = []
        self._main_window: "MainWindow | None" = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Title
        title = QLabel("Texture Properties")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Texture name group
        texture_group = QGroupBox("Texture")
        texture_layout = QFormLayout(texture_group)
        texture_layout.setSpacing(3)

        self.texture_name = QLineEdit()
        self.texture_name.setPlaceholderText("common/caulk")
        texture_layout.addRow("Name:", self.texture_name)

        # Browse button - opens texture browser
        self._browse_btn = QPushButton("Browse...")
        self._browse_btn.setToolTip("Open texture browser (T)")
        self._browse_btn.clicked.connect(self._on_browse_clicked)
        texture_layout.addRow("", self._browse_btn)

        layout.addWidget(texture_group)

        # Texture alignment group
        align_group = QGroupBox("Alignment")
        align_layout = QFormLayout(align_group)
        align_layout.setSpacing(3)

        # Offset
        offset_widget = QWidget()
        offset_layout = QHBoxLayout(offset_widget)
        offset_layout.setContentsMargins(0, 0, 0, 0)
        offset_layout.setSpacing(5)

        self.offset_x = QSpinBox()
        self.offset_x.setRange(-4096, 4096)
        self.offset_x.setSingleStep(1)
        offset_layout.addWidget(QLabel("X:"))
        offset_layout.addWidget(self.offset_x)

        self.offset_y = QSpinBox()
        self.offset_y.setRange(-4096, 4096)
        self.offset_y.setSingleStep(1)
        offset_layout.addWidget(QLabel("Y:"))
        offset_layout.addWidget(self.offset_y)

        align_layout.addRow("Offset:", offset_widget)

        # Scale
        scale_widget = QWidget()
        scale_layout = QHBoxLayout(scale_widget)
        scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.setSpacing(5)

        self.scale_x = QDoubleSpinBox()
        self.scale_x.setRange(0.01, 100.0)
        self.scale_x.setSingleStep(0.1)
        self.scale_x.setValue(1.0)
        self.scale_x.setDecimals(2)
        scale_layout.addWidget(QLabel("X:"))
        scale_layout.addWidget(self.scale_x)

        self.scale_y = QDoubleSpinBox()
        self.scale_y.setRange(0.01, 100.0)
        self.scale_y.setSingleStep(0.1)
        self.scale_y.setValue(1.0)
        self.scale_y.setDecimals(2)
        scale_layout.addWidget(QLabel("Y:"))
        scale_layout.addWidget(self.scale_y)

        align_layout.addRow("Scale:", scale_widget)

        # Rotation
        self.rotation = QDoubleSpinBox()
        self.rotation.setRange(-360.0, 360.0)
        self.rotation.setSingleStep(15.0)
        self.rotation.setValue(0.0)
        self.rotation.setSuffix("°")
        align_layout.addRow("Rotation:", self.rotation)

        layout.addWidget(align_group)

        # Quick texture buttons (2 per row)
        quick_group = QGroupBox("Quick Apply")
        quick_layout = QVBoxLayout(quick_group)
        quick_layout.setSpacing(3)

        quick_textures = [
            ("Caulk", "common/caulk"),
            ("Clip", "common/clip"),
            ("Nodraw", "common/nodraw"),
            ("Trigger", "common/trigger"),
        ]

        # Create rows with 2 buttons each
        for i in range(0, len(quick_textures), 2):
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(3)

            # First button
            label1, texture1 = quick_textures[i]
            btn1 = QPushButton(label1)
            btn1.clicked.connect(lambda checked, t=texture1: self._apply_quick_texture(t))
            row_layout.addWidget(btn1)

            # Second button (if exists)
            if i + 1 < len(quick_textures):
                label2, texture2 = quick_textures[i + 1]
                btn2 = QPushButton(label2)
                btn2.clicked.connect(lambda checked, t=texture2: self._apply_quick_texture(t))
                row_layout.addWidget(btn2)

            quick_layout.addWidget(row_widget)

        layout.addWidget(quick_group)

        # Apply button
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self._on_apply)
        layout.addWidget(apply_btn)

        # Info label
        self.info_label = QLabel("No selection")
        self.info_label.setEnabled(False)  # Use disabled text color for secondary text
        layout.addWidget(self.info_label)

        layout.addStretch()

        # Connect signals
        self.texture_name.editingFinished.connect(self._on_texture_changed)
        self.offset_x.valueChanged.connect(self._on_alignment_changed)
        self.offset_y.valueChanged.connect(self._on_alignment_changed)
        self.scale_x.valueChanged.connect(self._on_alignment_changed)
        self.scale_y.valueChanged.connect(self._on_alignment_changed)
        self.rotation.valueChanged.connect(self._on_alignment_changed)

    def update_from_selection(self):
        """Update panel from current selection."""
        self._updating = True
        self._selected_faces = []

        brushes = self.document.get_selected_brushes()

        if not brushes:
            self.info_label.setText("No selection")
            self._set_enabled(False)
            self._updating = False
            return

        # Collect all planes from selected brushes (only actual brushes, not patches)
        for brush in brushes:
            if isinstance(brush, _Brush):
                self._selected_faces.extend(brush.planes)

        if not self._selected_faces:
            self.info_label.setText("No faces")
            self._set_enabled(False)
            self._updating = False
            return

        # Get texture info from first face (BrushPlane)
        first_face = self._selected_faces[0]

        # Check if all faces have the same shader
        all_same_texture = all(
            f.shader == first_face.shader for f in self._selected_faces
        )

        if all_same_texture:
            self.texture_name.setText(first_face.shader)
        else:
            self.texture_name.setText("")
            self.texture_name.setPlaceholderText("(multiple)")

        # Set offset/scale/rotation from first face's texture params
        self.offset_x.setValue(int(first_face.texture.offset_x))
        self.offset_y.setValue(int(first_face.texture.offset_y))
        self.scale_x.setValue(first_face.texture.scale_x)
        self.scale_y.setValue(first_face.texture.scale_y)
        self.rotation.setValue(first_face.texture.rotation)

        # Update info
        face_count = len(self._selected_faces)
        brush_count = len(brushes)
        if brush_count == 1:
            self.info_label.setText(f"{face_count} faces (1 brush)")
        else:
            self.info_label.setText(f"{face_count} faces ({brush_count} brushes)")

        self._set_enabled(True)
        self._updating = False

    def _set_enabled(self, enabled: bool):
        """Enable or disable input fields."""
        self.texture_name.setEnabled(enabled)
        self.offset_x.setEnabled(enabled)
        self.offset_y.setEnabled(enabled)
        self.scale_x.setEnabled(enabled)
        self.scale_y.setEnabled(enabled)
        self.rotation.setEnabled(enabled)

    def _on_texture_changed(self):
        """Handle texture name change."""
        if self._updating:
            return
        self._apply_changes()

    def _on_alignment_changed(self):
        """Handle alignment value change."""
        if self._updating:
            return
        self._apply_changes()

    def _on_apply(self):
        """Apply button clicked."""
        self._apply_changes()

    def _apply_quick_texture(self, texture: str):
        """Apply a quick texture to all selected faces."""
        if not self._selected_faces:
            return

        for face in self._selected_faces:
            face.shader = texture

        self.texture_name.setText(texture)
        self.document.modified = True
        self.properties_changed.emit()

    def _apply_changes(self):
        """Apply the current values to selected faces."""
        if not self._selected_faces:
            return

        shader = self.texture_name.text().strip()
        if not shader:
            shader = "common/caulk"

        offset_x = self.offset_x.value()
        offset_y = self.offset_y.value()
        scale_x = self.scale_x.value()
        scale_y = self.scale_y.value()
        rotation = self.rotation.value()

        for face in self._selected_faces:
            face.shader = shader
            face.texture.offset_x = float(offset_x)
            face.texture.offset_y = float(offset_y)
            face.texture.scale_x = scale_x
            face.texture.scale_y = scale_y
            face.texture.rotation = rotation

        self.document.modified = True
        self.properties_changed.emit()

    def set_document(self, document: "MapDocument"):
        """Set the document."""
        self.document = document
        self.update_from_selection()

    def set_main_window(self, main_window: "MainWindow"):
        """Set reference to the main window for texture browser access."""
        self._main_window = main_window

    def _on_browse_clicked(self):
        """Handle browse button click - open texture browser."""
        self.browse_requested.emit()

        # If we have a main window reference, show the texture browser
        if self._main_window is not None:
            self._main_window.show_texture_browser()
