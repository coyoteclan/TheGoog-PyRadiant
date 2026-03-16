"""Entity Properties Panel with tabs for Properties editing and Entity Tree browsing."""

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
    QLineEdit,
    QComboBox,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QSplitter,
    QHeaderView,
    QAbstractItemView,
    QTabWidget,
    QScrollArea,
    QFrame,
    QGridLayout,
    QGroupBox,
    QToolTip,
)

from ..core.entity_defs import get_entity_def, get_all_classnames, ENTITY_DEFINITIONS

if TYPE_CHECKING:
    from ..core import MapDocument, Entity


class EntityPropertiesPanel(QWidget):
    """Panel with tabs for entity properties editing and entity tree browsing."""

    # Signal emitted when entity properties are changed
    properties_changed = pyqtSignal()

    # Signal emitted when user wants to select an entity (centers 2D view)
    select_entity = pyqtSignal(int)  # entity_id

    # Signal emitted when user wants to go to an entity (moves 3D camera)
    goto_entity = pyqtSignal(int)  # entity_id

    def __init__(self, parent=None):
        super().__init__(parent)
        self._document: MapDocument | None = None
        self._current_entity: Entity | None = None
        self._updating = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the UI with tabs."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        main_layout.addWidget(self._tabs)

        # Properties tab
        self._properties_tab = self._create_properties_tab()
        self._tabs.addTab(self._properties_tab, "Properties")

        # Entity Tree tab
        self._tree_tab = self._create_tree_tab()
        self._tabs.addTab(self._tree_tab, "Entity Tree")

    def _create_properties_tab(self) -> QWidget:
        """Create the Properties tab for editing selected entity."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Entity info header
        header_layout = QHBoxLayout()

        self._classname_label = QLabel("No Selection")
        self._classname_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self._classname_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Description label
        self._description_label = QLabel("")
        self._description_label.setWordWrap(True)
        self._description_label.setStyleSheet("font-size: 10px;")
        self._description_label.setEnabled(False)  # Use disabled text color for secondary text
        layout.addWidget(self._description_label)

        # Scroll area for properties
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        self._properties_layout = QVBoxLayout(scroll_widget)
        self._properties_layout.setContentsMargins(0, 0, 0, 0)
        self._properties_layout.setSpacing(5)

        # Key-Value editing group
        self._keyvalue_group = QGroupBox("Key Values")
        self._keyvalue_layout = QGridLayout(self._keyvalue_group)
        self._keyvalue_layout.setContentsMargins(5, 10, 5, 5)
        self._keyvalue_layout.setSpacing(4)
        self._properties_layout.addWidget(self._keyvalue_group)

        # Spawnflags group
        self._spawnflags_group = QGroupBox("Spawnflags")
        self._spawnflags_layout = QVBoxLayout(self._spawnflags_group)
        self._spawnflags_layout.setContentsMargins(5, 10, 5, 5)
        self._spawnflags_layout.setSpacing(2)
        self._properties_layout.addWidget(self._spawnflags_group)

        # Custom properties group
        self._custom_group = QGroupBox("Custom Properties")
        self._custom_layout = QGridLayout(self._custom_group)
        self._custom_layout.setContentsMargins(5, 10, 5, 5)
        self._custom_layout.setSpacing(4)
        self._properties_layout.addWidget(self._custom_group)

        # Add new property row
        add_row = QHBoxLayout()
        self._new_key_edit = QLineEdit()
        self._new_key_edit.setPlaceholderText("Key")
        self._new_value_edit = QLineEdit()
        self._new_value_edit.setPlaceholderText("Value")
        self._add_btn = QPushButton("Add")
        self._add_btn.setFixedWidth(50)
        self._add_btn.clicked.connect(self._on_add_property)
        add_row.addWidget(self._new_key_edit)
        add_row.addWidget(self._new_value_edit)
        add_row.addWidget(self._add_btn)
        self._properties_layout.addLayout(add_row)

        self._properties_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Store widgets for dynamic property editing
        self._property_widgets: dict[str, QLineEdit] = {}
        self._spawnflag_widgets: dict[int, QCheckBox] = {}
        self._custom_property_widgets: dict[str, tuple[QLineEdit, QPushButton]] = {}

        return widget

    def _create_tree_tab(self) -> QWidget:
        """Create the Entity Tree tab for browsing entities."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

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

        # Key-Value table (read-only display)
        self._tree_table = QTableWidget()
        self._tree_table.setColumnCount(2)
        self._tree_table.setHorizontalHeaderLabels(["Key", "Value"])
        self._tree_table.horizontalHeader().setStretchLastSection(True)
        self._tree_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._tree_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._tree_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tree_table.setAlternatingRowColors(True)
        self._tree_table.verticalHeader().setVisible(False)
        bottom_layout.addWidget(self._tree_table)

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

        layout.addWidget(splitter)

        # Store reference to selected entity in tree
        self._tree_selected_entity: Entity | None = None
        self._tree_selected_entity_idx: int | None = None

        return widget

    def _connect_signals(self):
        """Connect widget signals."""
        self._tree.currentItemChanged.connect(self._on_tree_selection_changed)
        self._select_btn.clicked.connect(self._on_select_clicked)
        self._goto_btn.clicked.connect(self._on_goto_clicked)

    def set_document(self, document: MapDocument):
        """Set the document and update the panel."""
        self._document = document
        self._current_entity = None
        self.update_tree()
        self._update_properties_tab(None)

    def update_from_selection(self):
        """Update properties tab based on current selection."""
        if self._document is None:
            self._update_properties_tab(None)
            return

        # Get selected brushes (entity_idx, brush_idx) tuples
        selected_brushes = self._document.selection.selected_brushes

        entity = None

        # If brushes are selected, find their parent entity
        if selected_brushes:
            # Get the first selected brush's entity index
            entity_idx, brush_idx = next(iter(selected_brushes))
            if entity_idx < len(self._document.entities):
                entity = self._document.entities[entity_idx]

        self._current_entity = entity
        self._update_properties_tab(entity)

    def _update_properties_tab(self, entity: Entity | None):
        """Update the properties tab for the given entity."""
        # Clear existing widgets
        self._clear_property_widgets()

        if entity is None:
            self._classname_label.setText("No Selection")
            self._description_label.setText("Select an entity to edit its properties.")
            self._keyvalue_group.setVisible(False)
            self._spawnflags_group.setVisible(False)
            self._custom_group.setVisible(False)
            self._add_btn.setEnabled(False)
            return

        self._add_btn.setEnabled(True)

        # Get entity definition
        entity_def = get_entity_def(entity.classname)

        # Update header
        self._classname_label.setText(entity.classname)
        if entity_def:
            self._description_label.setText(entity_def.description)
        else:
            self._description_label.setText("Unknown entity type")

        # Build property editors
        self._keyvalue_group.setVisible(True)

        row = 0

        # Add defined properties with tooltips
        if entity_def:
            for prop_def in entity_def.properties:
                label = QLabel(f"{prop_def.name}:")
                label.setToolTip(prop_def.description)

                edit = QLineEdit()
                edit.setText(entity.properties.get(prop_def.name, prop_def.default))
                edit.setToolTip(prop_def.description)
                edit.setPlaceholderText(prop_def.default if prop_def.default else f"({prop_def.prop_type})")
                edit.editingFinished.connect(lambda key=prop_def.name: self._on_property_changed(key))

                self._keyvalue_layout.addWidget(label, row, 0)
                self._keyvalue_layout.addWidget(edit, row, 1)
                self._property_widgets[prop_def.name] = edit
                row += 1

        # Add origin/angles for point entities without explicit definition
        if not entity_def or "origin" not in [p.name for p in (entity_def.properties if entity_def else [])]:
            if entity.origin is not None:
                label = QLabel("origin:")
                edit = QLineEdit()
                edit.setText(entity.properties.get("origin", ""))
                edit.setToolTip("Entity position (X Y Z)")
                edit.editingFinished.connect(lambda: self._on_property_changed("origin"))
                self._keyvalue_layout.addWidget(label, row, 0)
                self._keyvalue_layout.addWidget(edit, row, 1)
                self._property_widgets["origin"] = edit
                row += 1

        # Spawnflags
        if entity_def and entity_def.spawnflags:
            self._spawnflags_group.setVisible(True)
            current_flags = int(entity.properties.get("spawnflags", "0"))

            for flag_value, flag_name in sorted(entity_def.spawnflags.items()):
                checkbox = QCheckBox(flag_name)
                checkbox.setChecked(bool(current_flags & flag_value))
                checkbox.stateChanged.connect(lambda state, fv=flag_value: self._on_spawnflag_changed(fv, state))
                self._spawnflags_layout.addWidget(checkbox)
                self._spawnflag_widgets[flag_value] = checkbox
        else:
            self._spawnflags_group.setVisible(False)

        # Custom properties (not in definition)
        defined_keys = set()
        if entity_def:
            defined_keys = {p.name for p in entity_def.properties}
        defined_keys.add("classname")
        defined_keys.add("spawnflags")

        custom_props = {k: v for k, v in entity.properties.items() if k not in defined_keys}

        if custom_props:
            self._custom_group.setVisible(True)
            custom_row = 0
            for key, value in sorted(custom_props.items()):
                label = QLabel(f"{key}:")
                edit = QLineEdit()
                edit.setText(value)
                edit.editingFinished.connect(lambda k=key: self._on_property_changed(k))

                remove_btn = QPushButton("X")
                remove_btn.setFixedWidth(24)
                remove_btn.setToolTip(f"Remove {key}")
                remove_btn.clicked.connect(lambda checked, k=key: self._on_remove_property(k))

                self._custom_layout.addWidget(label, custom_row, 0)
                self._custom_layout.addWidget(edit, custom_row, 1)
                self._custom_layout.addWidget(remove_btn, custom_row, 2)
                self._custom_property_widgets[key] = (edit, remove_btn)
                custom_row += 1
        else:
            self._custom_group.setVisible(False)

    def _clear_property_widgets(self):
        """Clear all dynamic property widgets."""
        # Clear keyvalue layout
        while self._keyvalue_layout.count():
            item = self._keyvalue_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear spawnflags layout
        while self._spawnflags_layout.count():
            item = self._spawnflags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Clear custom layout
        while self._custom_layout.count():
            item = self._custom_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._property_widgets.clear()
        self._spawnflag_widgets.clear()
        self._custom_property_widgets.clear()

    def _on_property_changed(self, key: str):
        """Handle property value change."""
        if self._updating or self._current_entity is None:
            return

        widget = self._property_widgets.get(key) or (
            self._custom_property_widgets.get(key, (None,))[0]
        )
        if widget is None:
            return

        value = widget.text().strip()

        if value:
            self._current_entity.properties[key] = value
        else:
            # Remove empty properties (except classname)
            if key != "classname" and key in self._current_entity.properties:
                del self._current_entity.properties[key]

        if self._document:
            self._document.modified = True

        self.properties_changed.emit()

    def _on_spawnflag_changed(self, flag_value: int, state: int):
        """Handle spawnflag checkbox change."""
        if self._updating or self._current_entity is None:
            return

        current_flags = int(self._current_entity.properties.get("spawnflags", "0"))

        if state == Qt.CheckState.Checked.value:
            current_flags |= flag_value
        else:
            current_flags &= ~flag_value

        if current_flags:
            self._current_entity.properties["spawnflags"] = str(current_flags)
        elif "spawnflags" in self._current_entity.properties:
            del self._current_entity.properties["spawnflags"]

        if self._document:
            self._document.modified = True

        self.properties_changed.emit()

    def _on_add_property(self):
        """Handle adding a new property."""
        if self._current_entity is None:
            return

        key = self._new_key_edit.text().strip()
        value = self._new_value_edit.text().strip()

        if not key:
            return

        self._current_entity.properties[key] = value
        self._new_key_edit.clear()
        self._new_value_edit.clear()

        if self._document:
            self._document.modified = True

        self._update_properties_tab(self._current_entity)
        self.properties_changed.emit()

    def _on_remove_property(self, key: str):
        """Handle removing a custom property."""
        if self._current_entity is None:
            return

        if key in self._current_entity.properties:
            del self._current_entity.properties[key]

        if self._document:
            self._document.modified = True

        self._update_properties_tab(self._current_entity)
        self.properties_changed.emit()

    # =========================================================================
    # Entity Tree Tab Methods
    # =========================================================================

    def update_tree(self):
        """Rebuild the entity tree from the document."""
        self._tree.clear()
        self._tree_selected_entity = None
        self._tree_selected_entity_idx = None
        self._update_tree_table(None)
        self._update_tree_buttons()

        if self._document is None:
            return

        # Group entities by classname with their indices
        # Store as (entity_idx, entity) tuples
        entities_by_class: dict[str, list[tuple[int, Entity]]] = defaultdict(list)

        for entity_idx, entity in enumerate(self._document.entities):
            entities_by_class[entity.classname].append((entity_idx, entity))

        # Sort classnames alphabetically
        sorted_classnames = sorted(entities_by_class.keys())

        for classname in sorted_classnames:
            entity_data = entities_by_class[classname]

            # Create parent item for classname
            class_item = QTreeWidgetItem([classname])
            class_item.setData(0, Qt.ItemDataRole.UserRole, None)
            self._tree.addTopLevelItem(class_item)

            # Add child items for each entity
            for entity_idx, entity in entity_data:
                display_name = self._get_entity_display_name(entity, entity_idx)
                entity_item = QTreeWidgetItem([display_name])
                entity_item.setData(0, Qt.ItemDataRole.UserRole, entity_idx)
                class_item.addChild(entity_item)

        # Expand worldspawn by default
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            if item and item.text(0) == "worldspawn":
                item.setExpanded(True)
                break

    def _get_entity_display_name(self, entity: Entity, entity_idx: int) -> str:
        """Get a display name for an entity."""
        # Use targetname if available
        targetname = entity.properties.get("targetname", "")
        if targetname:
            return targetname

        # Use model property for misc_model
        if entity.classname == "misc_model":
            model = entity.properties.get("model", "")
            if model:
                return model.split("/")[-1].split("\\")[-1]

        # Use origin if available
        origin = entity.origin
        if origin is not None:
            return f"({origin.x:.0f}, {origin.y:.0f}, {origin.z:.0f})"

        # Fallback to entity index
        return f"entity_{entity_idx}"

    def _on_tree_selection_changed(self, current: QTreeWidgetItem | None, previous: QTreeWidgetItem | None):
        """Handle tree selection change."""
        if current is None:
            self._tree_selected_entity = None
            self._tree_selected_entity_idx = None
            self._update_tree_table(None)
            self._update_tree_buttons()
            return

        entity_idx = current.data(0, Qt.ItemDataRole.UserRole)
        if entity_idx is None:
            # Parent item selected
            self._tree_selected_entity = None
            self._tree_selected_entity_idx = None
            self._update_tree_table(None)
            self._update_tree_buttons()
            return

        # Find entity by index
        if self._document and entity_idx < len(self._document.entities):
            self._tree_selected_entity = self._document.entities[entity_idx]
            self._tree_selected_entity_idx = entity_idx
            self._update_tree_table(self._tree_selected_entity)
            self._update_tree_buttons()

    def _update_tree_table(self, entity: Entity | None):
        """Update the key-value table in the tree tab."""
        self._tree_table.setRowCount(0)

        if entity is None:
            return

        # Sort properties: classname first, then alphabetically
        props = list(entity.properties.items())
        props.sort(key=lambda x: (0 if x[0] == "classname" else 1, x[0]))

        self._tree_table.setRowCount(len(props))

        for row, (key, value) in enumerate(props):
            key_item = QTableWidgetItem(key)
            value_item = QTableWidgetItem(value)

            # Make classname bold
            if key == "classname":
                font = key_item.font()
                font.setBold(True)
                key_item.setFont(font)
                value_item.setFont(font)

            self._tree_table.setItem(row, 0, key_item)
            self._tree_table.setItem(row, 1, value_item)

    def _update_tree_buttons(self):
        """Update button enabled states."""
        has_entity = self._tree_selected_entity is not None
        self._select_btn.setEnabled(has_entity)
        self._goto_btn.setEnabled(has_entity)

    def _on_select_clicked(self):
        """Handle Select button click."""
        if self._tree_selected_entity is not None and self._tree_selected_entity_idx is not None:
            self.select_entity.emit(self._tree_selected_entity_idx)

    def _on_goto_clicked(self):
        """Handle Go To Position button click."""
        if self._tree_selected_entity is not None and self._tree_selected_entity_idx is not None:
            self.goto_entity.emit(self._tree_selected_entity_idx)
