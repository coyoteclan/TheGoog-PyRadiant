"""File operations controller - Open, Save, Recent Files."""

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QFileDialog, QMessageBox, QProgressDialog, QApplication
from PyQt6.QtCore import QSettings, Qt

# Use new core module
from ...core import (
    MapDocument,
    events,
    DocumentLoadedEvent,
    DocumentModifiedEvent,
    DocumentClosingEvent,
)

if TYPE_CHECKING:
    from ..main_window import MainWindow


class FileController:
    """
    Handles all file operations.

    Responsibilities:
    - New, Open, Save, Save As
    - Recent files management
    - Dirty-state checking
    """

    MAX_RECENT_FILES = 10

    def __init__(self, main_window: "MainWindow") -> None:
        self._window = main_window
        self._settings = QSettings("CoD1Radiant", "Editor")
        self._recent_files: list[str] = self._load_recent_files()

    @property
    def document(self) -> MapDocument:
        return self._window.document

    @document.setter
    def document(self, doc: MapDocument) -> None:
        self._window.document = doc

    def _load_recent_files(self) -> list[str]:
        """Load recent files from settings."""
        recent = self._settings.value("recentFiles", [])
        if isinstance(recent, list):
            # Filter out non-existent files
            return [f for f in recent if Path(f).exists()]
        return []

    def _save_recent_files(self) -> None:
        """Save recent files to settings."""
        self._settings.setValue("recentFiles", self._recent_files)

    def _add_to_recent(self, filepath: str) -> None:
        """Add file to recent files list."""
        # Remove if already exists (to move to top)
        if filepath in self._recent_files:
            self._recent_files.remove(filepath)

        # Add at top
        self._recent_files.insert(0, filepath)

        # Limit size
        self._recent_files = self._recent_files[:self.MAX_RECENT_FILES]

        self._save_recent_files()

    def get_recent_files(self) -> list[str]:
        """Get list of recent files."""
        return self._recent_files.copy()

    def new_document(self) -> bool:
        """Create a new empty document."""
        if not self._check_save():
            return False

        # Notify closing
        if self.document and self.document.filepath:
            events.publish(DocumentClosingEvent(filepath=str(self.document.filepath)))

        # Create new document using core
        new_doc = MapDocument.new()
        self._window.set_document(new_doc)

        return True

    def open_document(self) -> bool:
        """Show open dialog and load a document."""
        if not self._check_save():
            return False

        filepath, _ = QFileDialog.getOpenFileName(
            self._window,
            "Open Map",
            self._get_last_directory(),
            "MAP files (*.map);;All files (*.*)"
        )

        if filepath:
            return self.load_file(filepath)
        return False

    def load_file(self, filepath: str) -> bool:
        """Load a map file with progress dialog using new parser."""
        path = Path(filepath)

        if not path.exists():
            QMessageBox.critical(
                self._window,
                "Error",
                f"File not found:\n{filepath}"
            )
            return False

        # Create progress dialog
        progress = QProgressDialog(
            f"Loading {path.name}...",
            None,  # No cancel button
            0, 100,
            self._window
        )
        progress.setWindowTitle("Loading Map")
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        progress.setValue(0)
        QApplication.processEvents()

        try:
            # Notify closing of old document
            if self.document and self.document.filepath:
                events.publish(DocumentClosingEvent(filepath=str(self.document.filepath)))

            # Parse using new MapDocument.load()
            progress.setLabelText("Parsing MAP file...")
            progress.setValue(10)
            QApplication.processEvents()

            new_document = MapDocument.load(filepath)

            # Count geometry types
            progress.setLabelText("Computing brush geometry...")
            progress.setValue(40)
            QApplication.processEvents()

            brush_count = 0
            patch_count = 0
            terrain_count = 0
            curve_count = 0

            for entity_idx, brush_idx, brush in new_document.iter_all_geometry():
                if brush.is_regular:
                    brush_count += 1
                elif brush.is_terrain:
                    terrain_count += 1
                    patch_count += 1
                elif brush.is_curve:
                    curve_count += 1
                    patch_count += 1

            progress.setLabelText("Finalizing...")
            progress.setValue(80)
            QApplication.processEvents()

            # Set as active document
            self._window.set_document(new_document)
            self._add_to_recent(filepath)
            self._settings.setValue("lastDirectory", str(path.parent))

            progress.setValue(100)
            progress.close()

            events.publish(DocumentLoadedEvent(
                filepath=filepath,
                brush_count=brush_count,
                patch_count=patch_count,
                entity_count=new_document.entity_count
            ))

            return True

        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self._window,
                "Error",
                f"Failed to load map:\n{e}"
            )
            import traceback
            traceback.print_exc()
            return False

    def save_document(self) -> bool:
        """Save the current document."""
        if self.document and self.document.filepath:
            return self._save_to_file(str(self.document.filepath))
        return self.save_document_as()

    def save_document_as(self) -> bool:
        """Save document with new name."""
        filepath, _ = QFileDialog.getSaveFileName(
            self._window,
            "Save Map As",
            self._get_last_directory(),
            "MAP files (*.map);;All files (*.*)"
        )

        if filepath:
            # Ensure .map extension
            if not filepath.lower().endswith('.map'):
                filepath += '.map'
            return self._save_to_file(filepath)
        return False

    def _save_to_file(self, filepath: str) -> bool:
        """Write document to file using new save method."""
        try:
            # Use MapDocument.save() which wraps CoD1Map.save()
            self.document.save(filepath)

            self._add_to_recent(filepath)
            self._settings.setValue("lastDirectory", str(Path(filepath).parent))

            return True

        except Exception as e:
            QMessageBox.critical(
                self._window,
                "Error",
                f"Failed to save file:\n{e}"
            )
            import traceback
            traceback.print_exc()
            return False

    def _check_save(self) -> bool:
        """
        Check if document needs saving before closing.

        Returns:
            True if OK to proceed (saved or discarded)
            False if user cancelled
        """
        if not self.document or not self.document.modified:
            return True

        result = QMessageBox.question(
            self._window,
            "Unsaved Changes",
            "The document has been modified.\n\nSave changes before closing?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save
        )

        if result == QMessageBox.StandardButton.Save:
            return self.save_document()
        elif result == QMessageBox.StandardButton.Cancel:
            return False

        # Discard
        return True

    def _get_last_directory(self) -> str:
        """Get last used directory."""
        return self._settings.value("lastDirectory", "")

    def check_save_before_close(self) -> bool:
        """Public method for close event handling."""
        return self._check_save()
