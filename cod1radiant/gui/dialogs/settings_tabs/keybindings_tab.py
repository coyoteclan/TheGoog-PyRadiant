"""Keybindings settings tab for the settings dialog."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)


# Default keybindings for the editor
DEFAULT_KEYBINDINGS = [
    ("New", "Ctrl+N"),
    ("Open", "Ctrl+O"),
    ("Save", "Ctrl+S"),
    ("Save As", "Ctrl+Shift+S"),
    ("Undo", "Ctrl+Z"),
    ("Redo", "Ctrl+Y"),
    ("Delete", "Delete / Backspace"),
    ("Duplicate", "Ctrl+D"),
    ("Select All", "Ctrl+A"),
    ("Deselect", "Escape"),
    ("Cycle 2D View", "Ctrl+Tab"),
    ("Top View (XY)", "Ctrl+1"),
    ("Front View (XZ)", "Ctrl+2"),
    ("Side View (YZ)", "Ctrl+3"),
    ("Grid Larger", "]"),
    ("Grid Smaller", "["),
    ("Rotate Z (CW)", "R"),
    ("Rotate Z (CCW)", "Shift+R"),
    ("Rotate X", "Ctrl+R"),
    ("Rotate Y", "Alt+R"),
    ("Scale Up", "Ctrl+]"),
    ("Scale Down", "Ctrl+["),
    ("Create Block", "Ctrl+B"),
    ("Toggle Edge Mode", "E"),
    ("Texture Browser", "T"),
    ("Surface Inspector", "S"),
    ("Entity List", "L"),
    ("Toggle Grid (3D)", "G"),
    ("Toggle Wireframe (3D)", "F"),
    ("Toggle Frustum Culling", "C"),
    ("Toggle Batched Rendering", "B"),
    ("Toggle Octree Picking", "O"),
    ("Toggle Entity Markers", "M"),
    ("Reset Camera", "Home"),
]


class KeybindingsTab(QWidget):
    """Keybindings settings tab (read-only for now)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the tab UI."""
        layout = QVBoxLayout(self)

        info_label = QLabel("Current keyboard shortcuts (read-only)")
        info_label.setEnabled(False)
        layout.addWidget(info_label)

        # Keybindings table
        self.keybindings_table = QTableWidget()
        self.keybindings_table.setColumnCount(2)
        self.keybindings_table.setHorizontalHeaderLabels(["Action", "Shortcut"])
        self.keybindings_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.keybindings_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.keybindings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.keybindings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        # Populate with default keybindings
        self.keybindings_table.setRowCount(len(DEFAULT_KEYBINDINGS))
        for row, (action, shortcut) in enumerate(DEFAULT_KEYBINDINGS):
            self.keybindings_table.setItem(row, 0, QTableWidgetItem(action))
            self.keybindings_table.setItem(row, 1, QTableWidgetItem(shortcut))

        layout.addWidget(self.keybindings_table)
