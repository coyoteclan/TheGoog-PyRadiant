"""Info panel for displaying map statistics."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QScrollArea,
    QFrame,
    QGridLayout,
)

if TYPE_CHECKING:
    from ..core import MapDocument


class InfoPanel(QWidget):
    """Panel for displaying map statistics."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: MapDocument | None = None
        self._setup_ui()

    def _setup_ui(self):
        """Set up the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Title
        title = QLabel("Map Info")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        main_layout.addWidget(title)

        # Scroll area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # World group
        world_group = QGroupBox("World")
        world_layout = QGridLayout(world_group)
        world_layout.setContentsMargins(8, 12, 8, 8)
        world_layout.setSpacing(4)

        self._brushes_label = QLabel("0")
        self._curves_label = QLabel("0")
        self._terrain_label = QLabel("0")
        self._world_total_label = QLabel("0")

        world_layout.addWidget(QLabel("Brushes:"), 0, 0)
        world_layout.addWidget(self._brushes_label, 0, 1, Qt.AlignmentFlag.AlignRight)
        world_layout.addWidget(QLabel("Curves:"), 1, 0)
        world_layout.addWidget(self._curves_label, 1, 1, Qt.AlignmentFlag.AlignRight)
        world_layout.addWidget(QLabel("Terrain:"), 2, 0)
        world_layout.addWidget(self._terrain_label, 2, 1, Qt.AlignmentFlag.AlignRight)

        # Separator line
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        world_layout.addWidget(separator1, 3, 0, 1, 2)

        total_label = QLabel("Total:")
        total_label.setStyleSheet("font-weight: bold;")
        world_layout.addWidget(total_label, 4, 0)
        self._world_total_label.setStyleSheet("font-weight: bold;")
        world_layout.addWidget(self._world_total_label, 4, 1, Qt.AlignmentFlag.AlignRight)

        scroll_layout.addWidget(world_group)

        # Entity group
        entity_group = QGroupBox("Entity")
        entity_layout = QGridLayout(entity_group)
        entity_layout.setContentsMargins(8, 12, 8, 8)
        entity_layout.setSpacing(4)

        self._brush_entities_label = QLabel("0")
        self._model_entities_label = QLabel("0")

        entity_layout.addWidget(QLabel("Brush Entities:"), 0, 0)
        entity_layout.addWidget(self._brush_entities_label, 0, 1, Qt.AlignmentFlag.AlignRight)
        entity_layout.addWidget(QLabel("Model Entities:"), 1, 0)
        entity_layout.addWidget(self._model_entities_label, 1, 1, Qt.AlignmentFlag.AlignRight)

        scroll_layout.addWidget(entity_group)

        # Entity Breakdown group
        breakdown_group = QGroupBox("Entity Breakdown")
        self._breakdown_layout = QGridLayout(breakdown_group)
        self._breakdown_layout.setContentsMargins(8, 12, 8, 8)
        self._breakdown_layout.setSpacing(4)

        # Placeholder for entity breakdown
        self._breakdown_labels: list[tuple[QLabel, QLabel]] = []

        scroll_layout.addWidget(breakdown_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def set_document(self, document: MapDocument):
        """Set the document and update statistics."""
        self._document = document
        self.update_statistics()

    def update_statistics(self):
        """Update all statistics from the current document."""
        if self._document is None:
            self._clear_statistics()
            return

        # Count world geometry
        brush_count = 0
        curve_count = 0
        terrain_count = 0

        for entity in self._document.entities:
            for brush in entity.brushes:
                if brush.is_regular:
                    brush_count += 1
                elif brush.is_terrain:
                    terrain_count += 1
                elif brush.is_curve:
                    curve_count += 1

        self._brushes_label.setText(str(brush_count))
        self._curves_label.setText(str(curve_count))
        self._terrain_label.setText(str(terrain_count))
        self._world_total_label.setText(str(brush_count + curve_count + terrain_count))

        # Count entity types
        brush_entities = 0  # script_brushmodel
        model_entities = 0  # misc_model

        # Entity breakdown by classname
        classname_counts: Counter[str] = Counter()

        for entity in self._document.entities:
            if entity.is_worldspawn:
                continue

            classname = entity.classname.lower()
            classname_counts[classname] += 1

            if classname == "script_brushmodel":
                brush_entities += 1
            elif classname == "misc_model":
                model_entities += 1

        self._brush_entities_label.setText(str(brush_entities))
        self._model_entities_label.setText(str(model_entities))

        # Update entity breakdown
        self._update_breakdown(classname_counts)

    def _update_breakdown(self, classname_counts: Counter[str]):
        """Update the entity breakdown display."""
        # Clear existing labels
        for name_label, count_label in self._breakdown_labels:
            self._breakdown_layout.removeWidget(name_label)
            self._breakdown_layout.removeWidget(count_label)
            name_label.deleteLater()
            count_label.deleteLater()
        self._breakdown_labels.clear()

        # Sort by count (descending), then by name
        sorted_items = sorted(classname_counts.items(), key=lambda x: (-x[1], x[0]))

        for row, (classname, count) in enumerate(sorted_items):
            name_label = QLabel(classname)
            count_label = QLabel(str(count))

            self._breakdown_layout.addWidget(name_label, row, 0)
            self._breakdown_layout.addWidget(count_label, row, 1, Qt.AlignmentFlag.AlignRight)

            self._breakdown_labels.append((name_label, count_label))

        # Add "No entities" message if empty
        if not sorted_items:
            no_entities_label = QLabel("No entities")
            no_entities_label.setEnabled(False)  # Use disabled text color for secondary text
            empty_label = QLabel("")
            self._breakdown_layout.addWidget(no_entities_label, 0, 0)
            self._breakdown_layout.addWidget(empty_label, 0, 1)
            self._breakdown_labels.append((no_entities_label, empty_label))

    def _clear_statistics(self):
        """Clear all statistics display."""
        self._brushes_label.setText("0")
        self._curves_label.setText("0")
        self._terrain_label.setText("0")
        self._world_total_label.setText("0")
        self._brush_entities_label.setText("0")
        self._model_entities_label.setText("0")
        self._update_breakdown(Counter())
