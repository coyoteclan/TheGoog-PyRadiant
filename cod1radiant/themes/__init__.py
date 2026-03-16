"""Theme management for CoD1 Radiant Editor.

This module handles loading and managing UI themes (Qt stylesheets).
Themes are stored as .qss files in this directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

# Theme directory
THEMES_DIR = Path(__file__).parent

# Theme registry: theme_key -> display_name
THEME_NAMES: Dict[str, str] = {
    "dark": "Dark",
    "light": "Light",
    "blue_ocean": "Blue Ocean",
    "forest_green": "Forest Green",
    "midnight": "Midnight",
    "custom": "Custom...",
}

# Cache for loaded stylesheets
_stylesheet_cache: Dict[str, str] = {}


def get_theme_names() -> Dict[str, str]:
    """Get dictionary of theme keys to display names."""
    return THEME_NAMES.copy()


def get_available_themes() -> list[str]:
    """Get list of available theme keys (excluding 'custom')."""
    return [key for key in THEME_NAMES.keys() if key != "custom"]


def load_stylesheet(theme_key: str, use_cache: bool = True) -> str:
    """Load a stylesheet by theme key.

    Args:
        theme_key: The theme identifier (e.g., 'dark', 'light')
        use_cache: Whether to use cached stylesheet if available

    Returns:
        The stylesheet content as a string, or empty string if not found.
    """
    if use_cache and theme_key in _stylesheet_cache:
        return _stylesheet_cache[theme_key]

    qss_path = THEMES_DIR / f"{theme_key}.qss"

    if not qss_path.exists():
        return ""

    try:
        content = qss_path.read_text(encoding="utf-8")
        _stylesheet_cache[theme_key] = content
        return content
    except Exception as e:
        print(f"Failed to load theme '{theme_key}': {e}")
        return ""


def load_custom_stylesheet(file_path: str) -> str:
    """Load a custom stylesheet from an arbitrary path.

    Args:
        file_path: Path to the .qss file

    Returns:
        The stylesheet content as a string, or empty string if not found.
    """
    path = Path(file_path)

    if not path.exists():
        return ""

    try:
        return path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to load custom stylesheet '{file_path}': {e}")
        return ""


def clear_cache():
    """Clear the stylesheet cache."""
    _stylesheet_cache.clear()


def get_density_stylesheet(density: str) -> str:
    """Load a UI density modifier stylesheet.

    Args:
        density: The density mode ('compact', 'semi_compact', or 'normal')

    Returns:
        The density stylesheet content, or empty string for 'normal'.
    """
    if density == "normal":
        return ""

    qss_path = THEMES_DIR / f"density_{density}.qss"

    if not qss_path.exists():
        return ""

    try:
        return qss_path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Failed to load density stylesheet '{density}': {e}")
        return ""
