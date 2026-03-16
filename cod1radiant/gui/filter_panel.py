"""Filter panel for controlling visibility of map elements."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QGroupBox,
    QScrollArea,
    QPushButton,
    QFrame,
)

from ..core import events, FilterChangedEvent

if TYPE_CHECKING:
    from ..core import MapDocument


# =============================================================================
# FILTER DEFINITIONS
# =============================================================================

# Brushes/Surfaces filter - combined group
BRUSH_FILTERS = [
    # Geometry types
    ("brushes", "Brushes", True),
    ("curves", "Curves (Patches)", True),
    ("terrain", "Terrain", True),

    # Texture-based filters
    ("skybox", "Skybox", True),
    ("water", "Water", True),
    ("alpha", "Translucent (Alpha)", True),

    # Tool textures (common/)
    ("caulk", "Caulk", True),
    ("clip", "Clip", True),
    ("portals", "Portals", True),
    ("trigger_texture", "Trigger Texture", True),  # Renamed to avoid conflict with entity trigger
    ("decals", "Decals", True),
    ("hint_skip", "Hint/Skip", True),

    # Content flags based
    ("structural", "Structural", True),
    ("detail", "Detail", True),
    ("weapon_clip", "Weapon Clip", True),
    ("non_colliding", "Non-Colliding", True),
]

# Entity filter categories
ENTITY_FILTERS = [
    ("entities", "Entities", True),
    ("lights", "Lights", True),
    ("misc_models", "Misc Models", True),
    ("script_models", "Script Models", True),
    ("funcs", "Funcs", True),
    ("trigger_entities", "Triggers", True),  # Renamed to avoid conflict with brush trigger
    ("info", "Info", True),
    ("weapons", "Weapons", True),
    ("ammo_items", "Ammo/Items", True),
]


class FilterPanel(QWidget):
    """Panel for filtering visible map elements."""

    # Signal emitted when any filter changes
    filters_changed = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_checkboxes: dict[str, QCheckBox] = {}
        self._updating = False

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """Set up the UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Title
        title = QLabel("Filter")
        title.setStyleSheet("font-weight: bold; font-size: 12px;")
        main_layout.addWidget(title)

        # Quick actions row 1: All, None, Invert
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)

        self.show_all_btn = QPushButton("All")
        self.show_all_btn.setToolTip("Check all checkboxes")
        self.show_all_btn.setFixedHeight(24)
        self.show_all_btn.clicked.connect(self._check_all)
        actions_layout.addWidget(self.show_all_btn)

        self.hide_all_btn = QPushButton("None")
        self.hide_all_btn.setToolTip("Uncheck all checkboxes")
        self.hide_all_btn.setFixedHeight(24)
        self.hide_all_btn.clicked.connect(self._uncheck_all)
        actions_layout.addWidget(self.hide_all_btn)

        self.invert_btn = QPushButton("Invert")
        self.invert_btn.setToolTip("Invert all checkboxes")
        self.invert_btn.setFixedHeight(24)
        self.invert_btn.clicked.connect(self._invert_all)
        actions_layout.addWidget(self.invert_btn)

        main_layout.addLayout(actions_layout)

        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.setToolTip("Apply filter settings to viewports")
        self.apply_btn.setFixedHeight(28)
        self.apply_btn.setStyleSheet("font-weight: bold;")
        self.apply_btn.clicked.connect(self._apply_filters)
        main_layout.addWidget(self.apply_btn)

        # Scroll area for filter groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # Brushes/Surfaces group (combined)
        brushes_group = self._create_filter_group("Surfaces", BRUSH_FILTERS)
        scroll_layout.addWidget(brushes_group)

        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        scroll_layout.addWidget(separator)

        # Entities group
        entities_group = self._create_filter_group("Entities", ENTITY_FILTERS)
        scroll_layout.addWidget(entities_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _create_filter_group(self, title: str, filters: list[tuple[str, str, bool]]) -> QGroupBox:
        """Create a filter group with checkboxes."""
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        for key, display_name, default_visible in filters:
            checkbox = QCheckBox(display_name)
            checkbox.setChecked(default_visible)
            checkbox.setToolTip(f"Show/hide {display_name.lower()}")
            layout.addWidget(checkbox)
            self._filter_checkboxes[key] = checkbox

        return group

    def _connect_signals(self):
        """Connect checkbox signals."""
        # Checkboxes no longer directly emit filters_changed
        # User must click Apply button to apply changes
        pass

    def _apply_filters(self):
        """Apply current checkbox state to the viewports via Event-Bus."""
        filters = self.get_filters()

        # Publish event for viewports (they subscribe to FilterChangedEvent)
        events.publish(FilterChangedEvent(filters=filters))

        # Also emit Qt signal for MainWindow logging
        self.filters_changed.emit(filters)

    def get_filters(self) -> dict[str, bool]:
        """Get current filter state."""
        return {key: cb.isChecked() for key, cb in self._filter_checkboxes.items()}

    def set_filters(self, filters: dict[str, bool]):
        """Set filter state from dictionary."""
        self._updating = True
        try:
            for key, visible in filters.items():
                if key in self._filter_checkboxes:
                    self._filter_checkboxes[key].setChecked(visible)
        finally:
            self._updating = False

        # Publish event and emit signal
        current_filters = self.get_filters()
        events.publish(FilterChangedEvent(filters=current_filters))
        self.filters_changed.emit(current_filters)

    def _check_all(self):
        """Check all checkboxes (does not apply filters)."""
        for checkbox in self._filter_checkboxes.values():
            checkbox.setChecked(True)

    def _uncheck_all(self):
        """Uncheck all checkboxes (does not apply filters)."""
        for checkbox in self._filter_checkboxes.values():
            checkbox.setChecked(False)

    def _invert_all(self):
        """Invert all checkbox states (does not apply filters)."""
        for checkbox in self._filter_checkboxes.values():
            checkbox.setChecked(not checkbox.isChecked())

    def is_filter_enabled(self, key: str) -> bool:
        """Check if a specific filter is enabled."""
        if key in self._filter_checkboxes:
            return self._filter_checkboxes[key].isChecked()
        return True  # Default to visible if filter not found


# =============================================================================
# BRUSH FILTER MATCHER
# =============================================================================

class BrushFilterMatcher:
    """
    Matches brushes against filter criteria.

    Filter logic based on CoD1 MAP format:
    - Content flags: structural (0), detail (134217728), non_colliding (134217732), weapon_clip (134226048)
    - Texture patterns: sky/, common/caulk, common/clip, etc.
    - Brush types: normal brush vs patch (patchDef5, patchTerrainDef3)
    """

    # Content flag values from COD1_MAP_FORMAT_DOCUMENTATION.md
    CONTENT_FLAGS = {
        "structural": 0,            # SOLID - Standard collision
        "detail": 134217728,        # DETAIL - No BSP split
        "non_colliding": 134217732, # NONCOLLIDING - No collision
        "weapon_clip": 134226048,   # WEAPONCLIP - Weapon collision only
    }

    # Texture patterns for filter matching
    # Based on common/ tool shaders and surface type prefixes
    # Note: patterns are matched with 'in' operator, so "common/portal" matches "common/portalnodraw"
    TEXTURE_PATTERNS = {
        # Tool shaders (common/)
        "caulk": ["common/caulk"],
        "clip": ["common/clip"],
        "portals": ["common/portal", "common/areaportal"],  # portal, portalnodraw, portalcaulk + areaportal
        "trigger_texture": ["common/trigger"],  # Updated key to match BRUSH_FILTERS
        "hint_skip": ["common/hint", "common/skip"],

        # Surface types (texture name patterns)
        "skybox": ["sky/", "sky_"],
        "water": ["water", "liquid"],
        # alpha: handled specially - must NOT contain '@' (blend textures without surface type)
        "decals": ["decal@", "decal/"],
    }

    # Alpha/translucent texture patterns - these must NOT have '@' in name
    # (blend textures like alpha_grass, grass_brecourt - no surface type prefix)
    ALPHA_PATTERNS = ["alpha_", "glass", "_trans", "_alpha"]

    @classmethod
    def get_brush_categories(cls, brush) -> set[str]:
        """
        Determine which filter categories a brush belongs to.

        Args:
            brush: Brush object to categorize

        Returns:
            Set of category keys that match this brush
        """
        categories = set()

        # Check if this is a patch (curve/terrain)
        is_patch = getattr(brush, 'is_patch', False) or hasattr(brush, 'patch_type')
        is_terrain = getattr(brush, 'patch_type', '') == 'patchTerrainDef3'

        if is_terrain:
            categories.add("terrain")
        elif is_patch:
            categories.add("curves")
        else:
            categories.add("brushes")

        # Get content flag - check faces for content flags
        content_flag = cls._get_brush_content_flag(brush)

        # Match content flags to categories
        if content_flag == cls.CONTENT_FLAGS["detail"]:
            categories.add("detail")
        elif content_flag == cls.CONTENT_FLAGS["non_colliding"]:
            categories.add("non_colliding")
        elif content_flag == cls.CONTENT_FLAGS["weapon_clip"]:
            categories.add("weapon_clip")
        else:
            # Default structural (content flag 0)
            categories.add("structural")

        # Check textures on all faces
        for face in getattr(brush, 'faces', []):
            texture = getattr(face, 'texture', '').lower()

            # Check texture patterns
            for category, patterns in cls.TEXTURE_PATTERNS.items():
                for pattern in patterns:
                    if pattern in texture:
                        categories.add(category)
                        break

            # Special handling for alpha/translucent textures
            # These must NOT have '@' in the name (blend textures without surface type)
            if '@' not in texture:
                for pattern in cls.ALPHA_PATTERNS:
                    if pattern in texture:
                        categories.add("alpha")
                        break

        return categories

    @classmethod
    def _get_brush_content_flag(cls, brush) -> int:
        """Get the content flag from a brush (from its faces)."""
        # Check if brush has a direct content_flag attribute
        if hasattr(brush, 'content_flag'):
            return brush.content_flag

        # Otherwise check faces
        for face in getattr(brush, 'faces', []):
            content = getattr(face, 'content_flags', 0)
            if content != 0:
                return content

        return 0  # Default to structural

    @classmethod
    def should_show_brush(cls, brush, filters: dict[str, bool]) -> bool:
        """
        Determine if a brush should be shown based on current filters.

        Args:
            brush: Brush to check
            filters: Dictionary of filter key -> visible boolean

        Returns:
            True if brush should be visible
        """
        categories = cls.get_brush_categories(brush)

        # Brush is visible if ALL of its categories are enabled
        # This means if ANY category is disabled that matches, hide the brush
        for category in categories:
            if category in filters and not filters[category]:
                return False

        return True


# =============================================================================
# ENTITY FILTER MATCHER
# =============================================================================

class EntityFilterMatcher:
    """
    Matches entities against filter criteria based on their classname.

    Entity types from COD1_MAP_FORMAT_DOCUMENTATION.md:
    - light, corona
    - info_player_start, info_null, etc.
    - misc_model, misc_mg42, misc_turret
    - script_model, script_brushmodel
    - func_door, func_rotating, func_static, etc.
    - trigger_multiple, trigger_once, trigger_hurt
    - weapon_*, item_*
    """

    # Entity classname patterns for each filter category
    CLASSNAME_PATTERNS = {
        "lights": ["light", "corona"],
        "misc_models": ["misc_model", "misc_prefab"],
        "script_models": ["script_model", "script_brushmodel", "script_origin", "script_vehicle"],
        "funcs": ["func_group", "func_door", "func_rotating", "func_bobbing", "func_pendulum",
                  "func_static", "func_cullgroup", "func_door_rotating"],
        "trigger_entities": ["trigger_damage", "trigger_disk", "trigger_friendlychain", "trigger_hurt",
                             "trigger_lookat", "trigger_multiple", "trigger_once", "trigger_radius",
                             "trigger_use", "trigger_use_touch"],  # Updated key to match ENTITY_FILTERS
        "info": ["info_", "node_"],  # Include AI nodes
        "weapons": ["weapon_", "misc_mg42", "misc_turret"],
        "ammo_items": ["ammo_", "item_"],
    }

    @classmethod
    def get_entity_categories(cls, entity) -> set[str]:
        """
        Determine which filter categories an entity belongs to.

        Args:
            entity: Entity object to categorize

        Returns:
            Set of category keys that match this entity
        """
        categories = set()
        categories.add("entities")  # All entities belong to the entities category

        classname = getattr(entity, 'classname', '').lower()

        # Skip worldspawn - it's not filterable
        if classname == 'worldspawn':
            return categories

        for category, patterns in cls.CLASSNAME_PATTERNS.items():
            for pattern in patterns:
                if classname.startswith(pattern) or classname == pattern.rstrip('_'):
                    categories.add(category)
                    break

        return categories

    @classmethod
    def should_show_entity(cls, entity, filters: dict[str, bool]) -> bool:
        """
        Determine if an entity should be shown based on current filters.

        Args:
            entity: Entity to check
            filters: Dictionary of filter key -> visible boolean

        Returns:
            True if entity should be visible
        """
        # Skip worldspawn - always visible
        classname = getattr(entity, 'classname', '').lower()
        if classname == 'worldspawn':
            return True

        # First check if entities in general are enabled
        if not filters.get("entities", True):
            return False

        categories = cls.get_entity_categories(entity)

        # Entity is visible if ANY of its specific categories is enabled
        # (excluding the general "entities" category which we already checked)
        specific_categories = categories - {"entities"}

        if not specific_categories:
            # Entity doesn't match any specific category, show if entities enabled
            return True

        for category in specific_categories:
            if filters.get(category, True):
                return True

        return False
