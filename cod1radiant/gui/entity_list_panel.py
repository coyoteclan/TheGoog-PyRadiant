"""Entity list panel with tree view and key-value display."""

from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QSplitter,
    QHeaderView,
    QAbstractItemView,
)

if TYPE_CHECKING:
    from ..core import MapDocument, Entity


class EntityListPanel(QWidget):
    """Panel for browsing and selecting entities."""

    # Signal emitted when user wants to select an entity (centers 2D view)
    select_entity = pyqtSignal(int)  # entity_id

    # Signal emitted when user wants to go to an entity (moves 3D camera)
    goto_entity = pyqtSignal(int)  # entity_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: MapDocument | None = None
        self._current_entity: Entity | None = None
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Title
        title = QLabel("Entities")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        main_layout.addWidget(title)

        # Splitter for tree and key-value table
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Tree view for entities
        self._tree = QTreeWidget()
        self._tree.setHeaderLabels(["Entity"])
        self._tree.setRootIsDecorated(True)
        self._tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tree.setAlternatingRowColors(True)
        self._tree.header().setStretchLastSection(True)
        splitter.addWidget(self._tree)

        # Bottom section with key-value table and buttons
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(5)

        # Key-Value table
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Key", "Value"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        bottom_layout.addWidget(self._table)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)

        self._select_btn = QPushButton("Select")
        self._select_btn.setToolTip("Select entity and center 2D view on it")
        self._select_btn.setEnabled(False)
        button_layout.addWidget(self._select_btn)

        self._goto_btn = QPushButton("Go To Position")
        self._goto_btn.setToolTip("Move 3D camera to entity position")
        self._goto_btn.setEnabled(False)
        button_layout.addWidget(self._goto_btn)

        bottom_layout.addLayout(button_layout)
        splitter.addWidget(bottom_widget)

        # Set splitter sizes (60% tree, 40% table)
        splitter.setSizes([300, 200])

        main_layout.addWidget(splitter)

    def _connect_signals(self):
        """Connect widget signals."""
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self._select_btn.clicked.connect(self._on_select_clicked)
        self._goto_btn.clicked.connect(self._on_goto_clicked)

    def set_document(self, document: MapDocument):
        """Set the document and update the tree."""
        self._document = document
        self.update_tree()

    def update_tree(self):
        """Rebuild the entity tree from the document."""
        self._tree.clear()
        self._current_entity = None
        self._update_table(None)
        self._update_buttons()

        if self._document is None:
            return

        # Group entities by classname
        entities_by_class: dict[str, list[Entity]] = defaultdict(list)

        for entity in self._document.entities:
            entities_by_class[entity.classname].append(entity)

        # Sort classnames alphabetically
        sorted_classnames = sorted(entities_by_class.keys())

        for classname in sorted_classnames:
            entities = entities_by_class[classname]

            # Create parent item for classname
            class_item = QTreeWidgetItem([classname])
            class_item.setData(0, Qt.ItemDataRole.UserRole, None)  # No entity data for parent
            self._tree.addTopLevelItem(class_item)

            # Add child items for each entity
            for entity in entities:
                # Create display name
                display_name = self._get_entity_display_name(entity)
                entity_item = QTreeWidgetItem([display_name])
                entity_item.setData(0, Qt.ItemDataRole.UserRole, entity.index)
                class_item.addChild(entity_item)

        # Expand worldspawn by default if it exists
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item and item.text(0) == "worldspawn":
                item.setExpanded(True)
                break

    def _get_entity_display_name(self, entity: Entity) -> str:
        """Get a display name for an entity."""
        # Use targetname if available
        targetname = entity.properties.get("targetname", "")
        if targetname:
            return targetname

        # Use model property for misc_model
        if entity.classname == "misc_model":
            model = entity.properties.get("model", "")
            if model:
                # Extract filename from path
                return model.split("/")[-1].split("\\")[-1]

        # Use origin if available
        origin = entity.origin
        if origin is not None:
            return f"({origin.x:.0f}, {origin.y:.0f}, {origin.z:.0f})"

        # Fallback to entity index
        return f"entity_{entity.index}"

    def _on_tree_selection_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None):
        """Handle tree selection change."""
        if current is None:
            self._current_entity = None
            self._update_table(None)
            self._update_buttons()
            return

        entity_id = current.data(0, Qt.ItemDataRole.UserRole)
        if entity_id is None:
            # Parent item (classname) selected
            self._current_entity = None
            self._update_table(None)
            self._update_buttons()
            return

        # Find entity by index
        if self._document:
            self._current_entity = self._document.get_entity(entity_id)
            self._update_table(self._current_entity)
            self._update_buttons()

    def _update_table(self, entity: Entity | None):
        """Update the key-value table for the selected entity."""
        self._table.setRowCount(0)

        if entity is None:
            return

        # Sort properties alphabetically, but put 'classname' first
        props = list(entity.properties.items())
        props.sort(key=lambda x: (0 if x[0] == "classname" else 1, x[0]))

        self._table.setRowCount(len(props))

        for row, (key, value) in enumerate(props):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(value)

            # Make classname bold
            if key == "classname":
                font = key_item.font()
                font.setBold(True)
                key_item.setFont(font)
                value_item.setFont(font)

            self._table.setItem(row, 0, key_item)
            self._table.setItem(row, 1, value_item)

    def _update_buttons(self):
        """Update button enabled states."""
        has_entity = self._current_entity is not None
        self._select_btn.setEnabled(has_entity)
        self._goto_btn.setEnabled(has_entity)

    def _on_select_clicked(self):
        """Handle Select button click."""
        if self._current_entity is not None:
            self.select_entity.emit(self._current_entity.index)

    def _on_goto_clicked(self):
        """Handle Go To Position button click."""
        if self._current_entity is not None:
            self.goto_entity.emit(self._current_entity.index)

    def get_entity_center(self, entity_idx: int) -> np.ndarray | None:
        """Get the center position of an entity."""
        if self._document is None:
            return None

        entity = self._document.get_entity(entity_idx)
        if entity is None:
            return None

        # Entity.origin is already Vec3, convert to numpy
        origin = entity.origin
        if origin is not None:
            return np.array([origin.x, origin.y, origin.z])
        return None
