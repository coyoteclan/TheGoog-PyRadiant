"""
Texture Browser Panel - GUI for browsing and selecting textures.

Provides:
- Folder tree navigation
- Thumbnail grid view
- Search functionality
- Surface type filtering
- Integration with TextureManager
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QSize, QTimer, QThread, QObject
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QLabel,
    QPushButton,
    QAbstractItemView,
    QApplication,
    QButtonGroup,
)

from ..core.texture_manager import get_texture_manager, TextureInfo

if TYPE_CHECKING:
    from ..core import MapDocument

logger = logging.getLogger(__name__)

# Thumbnail size in the grid
THUMBNAIL_SIZE = 64
GRID_ICON_SIZE = QSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)


def normalize_plural(name: str) -> str:
    """
    Normalize plural forms to singular for better grouping.

    Examples:
        doors -> door
        roofs -> roof
        walls -> wall
        windows -> window

    Args:
        name: The folder/subfolder name to normalize

    Returns:
        Normalized singular form
    """
    name_lower = name.lower()

    # Common plural endings - order matters (check longer patterns first)
    # Handle special cases
    if name_lower.endswith("ies"):
        #eries -> ery (e.g., sceneries -> scenery)
        return name[:-3] + "y"
    elif name_lower.endswith("ves"):
        # ves -> f (e.g., rooves -> roof, but this is rare)
        return name[:-3] + "f"
    elif name_lower.endswith("es"):
        # Check if it's a word ending in s, x, z, ch, sh + es
        base = name[:-2]
        if name_lower.endswith(("sses", "xes", "zes", "ches", "shes")):
            return name[:-2]
        # boxes -> box, but not "es" alone words
        if len(base) > 2:
            return base
    elif name_lower.endswith("s") and not name_lower.endswith("ss"):
        # Simple plural: doors -> door, walls -> wall
        # But not: glass -> glas (wrong)
        if len(name) > 3:  # Minimum length to avoid breaking short words
            return name[:-1]

    return name


class TextureScanWorker(QObject):
    """Background worker for scanning textures."""
    finished = pyqtSignal()
    progress = pyqtSignal(int)  # Number of textures found so far

    def __init__(self, texture_manager):
        super().__init__()
        self._texture_manager = texture_manager

    def run(self):
        """Scan textures in background."""
        self._texture_manager.scan_textures()
        self.finished.emit()


class TextureBrowserPanel(QWidget):
    """
    Dock widget for browsing and selecting textures.

    Signals:
        texture_selected: Emitted when a texture is single-clicked (name)
        texture_applied: Emitted when a texture is double-clicked (name)
    """

    # Signal emitted when a texture is selected (single click)
    texture_selected = pyqtSignal(str)

    # Signal emitted when a texture should be applied (double click)
    texture_applied = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._texture_manager = get_texture_manager()
        self._current_folder: str = ""
        self._current_subfolders: list[str] = []  # Selected subfolders (can be multiple variants like door/doors)
        self._current_shader: str = ""  # Selected shader/surface type from tree
        self._search_query: str = ""
        self._loading = False
        self._browse_mode: str = "folder"  # "folder", "subfolder", or "shader"

        # Debounce timer for search
        self._search_timer = QTimer()
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._do_search)

        # Background scanning
        self._scan_thread: QThread | None = None
        self._scan_worker: TextureScanWorker | None = None

        # Placeholder icon (cached)
        self._placeholder_icon: QIcon | None = None

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the UI layout."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Main horizontal splitter
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # === LEFT PANEL (Search, Buttons, Category List) ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)

        # Search bar
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("Search textures...")
        self._search_edit.setClearButtonEnabled(True)
        left_layout.addWidget(self._search_edit)

        # Category toggle buttons
        category_layout = QHBoxLayout()
        category_layout.setSpacing(2)

        self._category_button_group = QButtonGroup(self)
        self._category_button_group.setExclusive(True)

        self._folder_btn = QPushButton("Folder")
        self._folder_btn.setCheckable(True)
        self._folder_btn.setChecked(True)
        self._category_button_group.addButton(self._folder_btn, 0)
        category_layout.addWidget(self._folder_btn)

        self._subfolder_btn = QPushButton("SubFolder")
        self._subfolder_btn.setCheckable(True)
        self._category_button_group.addButton(self._subfolder_btn, 1)
        category_layout.addWidget(self._subfolder_btn)

        self._shader_btn = QPushButton("Shader")
        self._shader_btn.setCheckable(True)
        self._category_button_group.addButton(self._shader_btn, 2)
        category_layout.addWidget(self._shader_btn)

        left_layout.addLayout(category_layout)

        # Category list - shows folders/subfolders/shaders based on selected category
        self._category_list = QListWidget()
        left_layout.addWidget(self._category_list, 1)

        left_panel.setMinimumWidth(150)
        self._splitter.addWidget(left_panel)

        # === RIGHT PANEL (Thumbnail Grid) ===
        self._thumbnail_list = QListWidget()
        self._thumbnail_list.setViewMode(QListWidget.ViewMode.IconMode)
        self._thumbnail_list.setIconSize(GRID_ICON_SIZE)
        self._thumbnail_list.setSpacing(5)
        self._thumbnail_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self._thumbnail_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._thumbnail_list.setWordWrap(True)
        self._thumbnail_list.setUniformItemSizes(True)
        self._splitter.addWidget(self._thumbnail_list)

        # Set initial splitter sizes
        self._splitter.setSizes([200, 400])

        main_layout.addWidget(self._splitter, 1)

        # === BOTTOM BAR ===
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(10)

        # Texture details (left side, stacked vertically)
        info_layout = QVBoxLayout()
        info_layout.setSpacing(0)

        self._texture_name_label = QLabel("No texture selected")
        self._texture_name_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(self._texture_name_label)

        self._texture_info_label = QLabel("")
        # Use disabled text color for secondary info (works with light/dark themes)
        self._texture_info_label.setEnabled(False)
        info_layout.addWidget(self._texture_info_label)

        bottom_layout.addLayout(info_layout)
        bottom_layout.addStretch()

        # Refresh button (right side)
        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.setToolTip("Rescan texture directory")
        bottom_layout.addWidget(self._refresh_btn)

        main_layout.addLayout(bottom_layout)

    def _connect_signals(self):
        """Connect widget signals."""
        self._search_edit.textChanged.connect(self._on_search_changed)
        self._category_button_group.buttonClicked.connect(self._on_category_changed)
        self._category_list.itemClicked.connect(self._on_category_item_clicked)
        self._thumbnail_list.itemClicked.connect(self._on_thumbnail_clicked)
        self._thumbnail_list.itemDoubleClicked.connect(self._on_thumbnail_double_clicked)
        self._refresh_btn.clicked.connect(self.refresh)

    def refresh(self):
        """Refresh the texture list by rescanning the texture directory in background."""
        if self._loading:
            return

        self._loading = True
        self._refresh_btn.setEnabled(False)
        self._refresh_btn.setText("Scanning...")

        # Clean up previous thread if any
        if self._scan_thread is not None:
            self._scan_thread.quit()
            self._scan_thread.wait()

        # Create worker and thread
        self._scan_thread = QThread()
        self._scan_worker = TextureScanWorker(self._texture_manager)
        self._scan_worker.moveToThread(self._scan_thread)

        # Connect signals
        self._scan_thread.started.connect(self._scan_worker.run)
        self._scan_worker.finished.connect(self._on_scan_finished)
        self._scan_worker.finished.connect(self._scan_thread.quit)

        # Start scanning
        self._scan_thread.start()

    def _on_scan_finished(self):
        """Called when background texture scan is complete."""
        # Update UI (runs on main thread)
        # Only update category list - don't load thumbnails until user selects a category
        self._update_category_list()
        # Clear thumbnail grid and show hint
        self._thumbnail_list.clear()

        self._loading = False
        self._refresh_btn.setEnabled(True)
        self._refresh_btn.setText("Refresh")

    def set_texture_path(self, path: Path | str):
        """Set the texture directory path and refresh."""
        self._texture_manager.set_texture_path(path)
        self.refresh()

    def _update_category_list(self):
        """Update the category list based on selected category button."""
        self._category_list.clear()

        if self._browse_mode == "folder":
            # Get folders and apply lowercase to avoid duplicates
            folders = self._texture_manager.get_texture_folders()
            # Use dict to deduplicate case-insensitively while preserving one version
            unique_folders: dict[str, str] = {}
            for folder in folders:
                key = folder.lower()
                if key not in unique_folders:
                    unique_folders[key] = folder
            # Sort by lowercase key and add items
            for key in sorted(unique_folders.keys()):
                item = QListWidgetItem(unique_folders[key])
                item.setData(Qt.ItemDataRole.UserRole, unique_folders[key])
                self._category_list.addItem(item)

        elif self._browse_mode == "subfolder":
            # Get subfolders and apply normalization to group singular/plural
            # e.g., "door" and "doors" become one entry
            subfolders = self._texture_manager.get_all_subfolders()
            # Key: normalized lowercase, Value: list of original names
            subfolder_groups: dict[str, list[str]] = {}
            for subfolder in subfolders:
                # Normalize plural to singular and lowercase
                normalized = normalize_plural(subfolder).lower()
                if normalized not in subfolder_groups:
                    subfolder_groups[normalized] = []
                subfolder_groups[normalized].append(subfolder)

            # For display, use the shortest name (usually singular)
            for key in sorted(subfolder_groups.keys()):
                originals = subfolder_groups[key]
                # Pick the shortest one for display (usually singular)
                display_name = min(originals, key=len)
                # Store all original names for texture lookup
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, originals)  # Store list of all variants
                self._category_list.addItem(item)

        elif self._browse_mode == "shader":
            # Get surface types and apply lowercase to avoid duplicates
            surface_types = self._texture_manager.get_all_surface_types()
            unique_shaders: dict[str, str] = {}
            for shader in surface_types:
                key = shader.lower()
                if key not in unique_shaders:
                    unique_shaders[key] = shader
            for key in sorted(unique_shaders.keys()):
                item = QListWidgetItem(unique_shaders[key])
                item.setData(Qt.ItemDataRole.UserRole, unique_shaders[key])
                self._category_list.addItem(item)

        # Don't auto-select - wait for user to choose a category
        # This prevents loading all textures at once

    def _on_category_changed(self, button: QPushButton):
        """Handle category button toggle."""
        if button == self._folder_btn:
            self._browse_mode = "folder"
            self._current_folder = ""
            self._current_subfolders = []
            self._current_shader = ""
        elif button == self._subfolder_btn:
            self._browse_mode = "subfolder"
            self._current_folder = ""
            self._current_subfolders = []
            self._current_shader = ""
        elif button == self._shader_btn:
            self._browse_mode = "shader"
            self._current_folder = ""
            self._current_subfolders = []
            self._current_shader = ""

        self._update_category_list()
        # Clear thumbnail grid - don't load textures until user selects a category
        self._thumbnail_list.clear()

    def _on_category_item_clicked(self, item: QListWidgetItem):
        """Handle category list item click."""
        value = item.data(Qt.ItemDataRole.UserRole)

        if self._browse_mode == "folder":
            self._current_folder = value
            self._current_subfolders = []
            self._current_shader = ""
        elif self._browse_mode == "subfolder":
            # Value is a list of subfolder variants (e.g., ["door", "doors"])
            if isinstance(value, list):
                self._current_subfolders = value
            else:
                self._current_subfolders = [value] if value else []
            self._current_folder = ""
            self._current_shader = ""
        elif self._browse_mode == "shader":
            self._current_shader = value
            self._current_folder = ""
            self._current_subfolders = []

        self._update_thumbnail_grid()

    def _update_thumbnail_grid(self, load_thumbnails: bool = True):
        """Update the thumbnail grid based on current folder/subfolder/shader and search.

        Args:
            load_thumbnails: If True, load all thumbnails immediately for the current selection.
        """
        self._thumbnail_list.clear()

        # Get textures based on current state
        if self._search_query:
            # Search mode - search across all textures
            textures = self._texture_manager.search_textures(self._search_query)
        elif self._browse_mode == "shader" and self._current_shader:
            # Shader mode - filter by surface type
            textures = self._texture_manager.get_textures_by_surface_type(self._current_shader)
        elif self._browse_mode == "subfolder" and self._current_subfolders:
            # SubFolder mode - filter by all subfolder variants (e.g., door + doors)
            textures = []
            for subfolder in self._current_subfolders:
                textures.extend(self._texture_manager.get_textures_by_subfolder(subfolder))
            # Remove duplicates (in case a texture matches multiple variants)
            seen = set()
            unique_textures = []
            for t in textures:
                if t.name not in seen:
                    seen.add(t.name)
                    unique_textures.append(t)
            textures = unique_textures
        elif self._browse_mode == "folder" and self._current_folder:
            # Folder mode - filter by folder
            textures = self._texture_manager.get_textures_in_folder(self._current_folder)
        else:
            # No selection - don't load all textures, show empty grid
            # User must select a folder/subfolder/shader first
            textures = []

        # Sort by name
        textures.sort(key=lambda t: t.name.lower())

        # Create list items
        placeholder = self._get_placeholder_icon()
        for texture_info in textures:
            item = QListWidgetItem()
            item.setText(self._get_display_name(texture_info.name))
            item.setData(Qt.ItemDataRole.UserRole, texture_info.name)
            item.setToolTip(texture_info.name)
            item.setIcon(placeholder)
            self._thumbnail_list.addItem(item)

        # Load thumbnails for all visible items
        if load_thumbnails:
            self._load_all_thumbnails()

    def _get_display_name(self, texture_name: str) -> str:
        """Get a shortened display name for the thumbnail grid."""
        # Get just the filename part
        if "/" in texture_name:
            name = texture_name.split("/")[-1]
        else:
            name = texture_name

        # Truncate if too long
        if len(name) > 15:
            return name[:12] + "..."
        return name

    def _get_placeholder_icon(self) -> QIcon:
        """Get cached placeholder icon for textures."""
        if self._placeholder_icon is None:
            pixmap = QPixmap(THUMBNAIL_SIZE, THUMBNAIL_SIZE)
            pixmap.fill(Qt.GlobalColor.darkGray)
            self._placeholder_icon = QIcon(pixmap)
        return self._placeholder_icon

    def _load_all_thumbnails(self):
        """Load thumbnails for all items in the grid."""
        count = self._thumbnail_list.count()
        for i in range(count):
            item = self._thumbnail_list.item(i)
            if item is None:
                continue
            texture_name = item.data(Qt.ItemDataRole.UserRole)
            if texture_name:
                thumbnail = self._texture_manager.get_thumbnail(texture_name)
                if thumbnail:
                    item.setIcon(QIcon(thumbnail))
            # Process events periodically to keep UI responsive
            if i % 20 == 0:
                QApplication.processEvents()

    def _on_search_changed(self, text: str):
        """Handle search text changes with debouncing."""
        self._search_query = text.strip()
        # Debounce: wait 300ms after typing stops
        self._search_timer.stop()
        self._search_timer.start(300)

    def _do_search(self):
        """Execute the search after debounce."""
        self._update_thumbnail_grid()

    def _on_thumbnail_clicked(self, item: QListWidgetItem):
        """Handle thumbnail single click - select texture."""
        texture_name = item.data(Qt.ItemDataRole.UserRole)
        if texture_name:
            # Load thumbnail on demand
            self._load_thumbnail_for_item(item, texture_name)
            self._update_info_bar(texture_name)
            self.texture_selected.emit(texture_name)

    def _load_thumbnail_for_item(self, item: QListWidgetItem, texture_name: str):
        """Load and set thumbnail for a specific item."""
        # Check if already loaded (not placeholder)
        thumbnail = self._texture_manager.get_thumbnail(texture_name)
        if thumbnail:
            item.setIcon(QIcon(thumbnail))

    def _on_thumbnail_double_clicked(self, item: QListWidgetItem):
        """Handle thumbnail double click - apply texture."""
        texture_name = item.data(Qt.ItemDataRole.UserRole)
        if texture_name:
            self.texture_applied.emit(texture_name)

    def _update_info_bar(self, texture_name: str):
        """Update the info bar with texture details."""
        info = self._texture_manager.get_texture_info(texture_name)
        if info:
            self._texture_name_label.setText(texture_name)

            details = []
            if info.width and info.height:
                details.append(f"{info.width}x{info.height}")
            if info.format:
                details.append(info.format.upper())
            if info.surface_type:
                details.append(f"Surface: {info.surface_type}")

            self._texture_info_label.setText(" | ".join(details) if details else str(info.path))
        else:
            self._texture_name_label.setText(texture_name)
            self._texture_info_label.setText("Texture info not available")

    def select_texture(self, texture_name: str):
        """
        Programmatically select a texture in the browser.

        Args:
            texture_name: Name of the texture to select
        """
        # Find and select the item
        for i in range(self._thumbnail_list.count()):
            item = self._thumbnail_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == texture_name:
                self._thumbnail_list.setCurrentItem(item)
                self._thumbnail_list.scrollToItem(item)
                self._update_info_bar(texture_name)
                break

    def get_selected_texture(self) -> Optional[str]:
        """Get the currently selected texture name."""
        item = self._thumbnail_list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None

    def clear_selection(self):
        """Clear the current selection."""
        self._thumbnail_list.clearSelection()
        self._texture_name_label.setText("No texture selected")
        self._texture_info_label.setText("")
