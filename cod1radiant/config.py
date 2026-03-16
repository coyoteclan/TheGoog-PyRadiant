"""Global configuration for CoD1 Radiant Editor.

UI stylesheets are now stored in the 'themes' module as separate .qss files.
Use `from cod1radiant import themes` to load stylesheets dynamically.
"""

from pathlib import Path

# Application info
APP_NAME = "CoD1 Radiant"
APP_VERSION = "0.1.0"

# Default paths
DEFAULT_GAME_PATH = Path("C:/Program Files/Call of Duty")
DEFAULT_TEXTURE_PATH = DEFAULT_GAME_PATH / "main" / "textures"

# Grid settings
DEFAULT_GRID_SIZE = 8
MIN_GRID_SIZE = 1
MAX_GRID_SIZE = 256
GRID_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256]

# Viewport settings
DEFAULT_NEAR_PLANE = 1.0
DEFAULT_FAR_PLANE = 16384.0
DEFAULT_FOV = 90.0
DEFAULT_CAMERA_SPEED = 500.0
DEFAULT_MOUSE_SENSITIVITY = 0.2

# Editor defaults
DEFAULT_TEXTURE = "common/caulk"
EPSILON = 0.0001  # Floating point comparison tolerance

# Colors (RGBA normalized) - Dark Theme (default)
COLORS = {
    "grid_major": (0.4, 0.4, 0.4, 1.0),
    "grid_minor": (0.2, 0.2, 0.2, 1.0),
    "selection": (1.0, 0.0, 0.0, 1.0),
    "brush_outline": (1.0, 1.0, 1.0, 1.0),
    "background_2d": (0.1, 0.1, 0.1, 1.0),
    "background_3d": (0.2, 0.2, 0.2, 1.0),
    "vao_color": (0.6, 0.6, 0.6, 1.0),
    "console": (0.12, 0.12, 0.12, 1.0),
}

# 2D Viewport brush colors by type (RGB normalized)
# Content flag colors (higher priority - override geometry type)
BRUSH_COLORS_2D = {
    # Content flag based (highest priority)
    "structural": (1.0, 1.0, 1.0),      # White
    "detail": (1.0, 1.0, 0.0),          # Yellow
    "weapon_clip": (0.5, 0.8, 1.0),     # Light blue
    "non_colliding": (1.0, 0.5, 0.8),   # Pink

    # Geometry type based (lower priority, used when content flag is structural)
    "brush": (1.0, 1.0, 1.0),           # White (same as structural)
    "curves": (0.6, 0.4, 0.2),          # Brown
    "terrain": (0.0, 1.0, 1.0),         # Cyan
}

# Light Theme colors
COLORS_LIGHT = {
    "grid_major": (0.7, 0.7, 0.7, 1.0),
    "grid_minor": (0.85, 0.85, 0.85, 1.0),
    "selection": (1.0, 0.0, 0.0, 1.0),
    "brush_outline": (0.0, 0.0, 0.0, 1.0),
    "background_2d": (0.95, 0.95, 0.95, 1.0),
    "background_3d": (0.85, 0.85, 0.9, 1.0),
    "vao_color": (0.5, 0.5, 0.55, 1.0),
    "console": (0.95, 0.95, 0.95, 1.0),
}

# Theme presets (viewport colors, not UI stylesheets)
THEMES = {
    "dark": COLORS,
    "light": COLORS_LIGHT,
}

# UI density mode names
# Icon sizes: compact=20x20, semi_compact=24x24, normal=32x32
UI_DENSITY_NAMES = {
    "compact": "Compact",
    "semi_compact": "Semi-Compact",
    "normal": "Normal",
}


# =============================================================================
# BACKWARDS COMPATIBILITY
# =============================================================================
# The following loads stylesheets from .qss files for backwards compatibility.
# New code should use the themes module directly:
#   from cod1radiant import themes
#   stylesheet = themes.load_stylesheet("dark")

def _load_legacy_stylesheets():
    """Load stylesheets from .qss files for backwards compatibility."""
    from . import themes

    stylesheets = {}
    for key in ["dark", "light", "blue_ocean", "forest_green", "midnight"]:
        stylesheets[key] = themes.load_stylesheet(key)

    return {
        "UI_STYLESHEETS": stylesheets,
        "THEME_NAMES": themes.get_theme_names(),
        "STYLESHEET_DARK": stylesheets.get("dark", ""),
        "STYLESHEET_LIGHT": stylesheets.get("light", ""),
        "STYLESHEET_BLUE_OCEAN": stylesheets.get("blue_ocean", ""),
        "STYLESHEET_FOREST_GREEN": stylesheets.get("forest_green", ""),
        "STYLESHEET_MIDNIGHT": stylesheets.get("midnight", ""),
        "STYLESHEET_SEMI_COMPACT": themes.get_density_stylesheet("semi_compact"),
        "STYLESHEET_COMPACT": themes.get_density_stylesheet("compact"),
    }


# Load stylesheets on import
_loaded = _load_legacy_stylesheets()
UI_STYLESHEETS = _loaded["UI_STYLESHEETS"]
THEME_NAMES = _loaded["THEME_NAMES"]
STYLESHEET_DARK = _loaded["STYLESHEET_DARK"]
STYLESHEET_LIGHT = _loaded["STYLESHEET_LIGHT"]
STYLESHEET_BLUE_OCEAN = _loaded["STYLESHEET_BLUE_OCEAN"]
STYLESHEET_FOREST_GREEN = _loaded["STYLESHEET_FOREST_GREEN"]
STYLESHEET_MIDNIGHT = _loaded["STYLESHEET_MIDNIGHT"]
STYLESHEET_SEMI_COMPACT = _loaded["STYLESHEET_SEMI_COMPACT"]
STYLESHEET_COMPACT = _loaded["STYLESHEET_COMPACT"]
del _loaded
