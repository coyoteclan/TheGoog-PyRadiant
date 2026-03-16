"""Icon loader utility for loading DDS toolbar icons with hover states.

The toolbar icons are 128x64 DDS files in DXT5 format.
Left half (64x64) = normal state
Right half (64x64) = hover state
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtGui import QIcon, QPixmap, QImage
from PyQt6.QtCore import QSize, QEvent, Qt
from PyQt6.QtWidgets import QToolButton

logger = logging.getLogger(__name__)

# Icon cache to avoid reloading
_icon_cache: dict[str, QIcon] = {}
_pixmap_cache: dict[tuple[str, str], QPixmap] = {}

# Path to icons directory
ICONS_DIR = Path(__file__).parent.parent / "resources" / "icons"


def _load_dds_image(filepath: Path) -> Optional[QImage]:
    """
    Load a DDS image file and convert to QImage.

    Supports DXT1 and DXT5 compressed formats commonly used in game assets.

    Args:
        filepath: Path to the DDS file

    Returns:
        QImage or None if loading failed
    """
    try:
        # Try using PIL/Pillow first (better DDS support)
        from PIL import Image

        img = Image.open(filepath)
        img = img.convert("RGBA")

        # Convert PIL Image to QImage
        data = img.tobytes("raw", "RGBA")
        qimg = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
        # Need to copy since data goes out of scope
        return qimg.copy()

    except ImportError:
        logger.warning("PIL not available, trying Qt native DDS loading")
    except Exception as e:
        logger.debug(f"PIL failed to load {filepath}: {e}")

    # Fallback: Try Qt's native image loading (may not support all DDS formats)
    try:
        qimg = QImage(str(filepath))
        if not qimg.isNull():
            return qimg
    except Exception as e:
        logger.debug(f"Qt failed to load {filepath}: {e}")

    return None


def load_toolbar_icon(name: str) -> Optional[QIcon]:
    """
    Load a toolbar icon with normal and hover states.

    The icon file is expected to be 128x64 with:
    - Left 64x64: normal state
    - Right 64x64: hover state

    Args:
        name: Icon name without extension (e.g., "save", "open")

    Returns:
        QIcon with normal and hover states, or None if not found
    """
    if name in _icon_cache:
        return _icon_cache[name]

    icon_path = ICONS_DIR / f"{name}.dds"
    if not icon_path.exists():
        logger.debug(f"Icon not found: {icon_path}")
        return None

    qimg = _load_dds_image(icon_path)
    if qimg is None:
        logger.warning(f"Failed to load icon: {icon_path}")
        return None

    # Split the image: left half = normal, right half = hover
    width = qimg.width()
    height = qimg.height()
    half_width = width // 2

    # Extract left half (normal state)
    normal_img = qimg.copy(0, 0, half_width, height)
    normal_pixmap = QPixmap.fromImage(normal_img)

    # Extract right half (hover state)
    hover_img = qimg.copy(half_width, 0, half_width, height)
    hover_pixmap = QPixmap.fromImage(hover_img)

    # Create QIcon with different states
    icon = QIcon()
    icon.addPixmap(normal_pixmap, QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(hover_pixmap, QIcon.Mode.Active, QIcon.State.Off)
    icon.addPixmap(hover_pixmap, QIcon.Mode.Selected, QIcon.State.Off)
    # For disabled state, use normal but Qt will auto-gray it
    icon.addPixmap(normal_pixmap, QIcon.Mode.Disabled, QIcon.State.Off)

    _icon_cache[name] = icon
    return icon


def load_icon_pixmap(name: str, state: str = "normal") -> Optional[QPixmap]:
    """
    Load a specific state of a toolbar icon as a QPixmap.

    Args:
        name: Icon name without extension
        state: "normal" or "hover"

    Returns:
        QPixmap or None if not found
    """
    cache_key = (name, state)
    if cache_key in _pixmap_cache:
        return _pixmap_cache[cache_key]

    icon_path = ICONS_DIR / f"{name}.dds"
    if not icon_path.exists():
        return None

    qimg = _load_dds_image(icon_path)
    if qimg is None:
        return None

    width = qimg.width()
    height = qimg.height()
    half_width = width // 2

    if state == "hover":
        img = qimg.copy(half_width, 0, half_width, height)
    else:
        img = qimg.copy(0, 0, half_width, height)

    pixmap = QPixmap.fromImage(img)
    _pixmap_cache[cache_key] = pixmap
    return pixmap


def get_available_icons() -> list[str]:
    """
    Get list of available icon names.

    Returns:
        List of icon names (without extension)
    """
    if not ICONS_DIR.exists():
        return []

    icons = []
    for f in ICONS_DIR.glob("*.dds"):
        # Skip special files
        if f.stem.startswith("_"):
            continue
        icons.append(f.stem)

    return sorted(icons)


def clear_icon_cache():
    """Clear the icon cache to free memory."""
    _icon_cache.clear()
    _pixmap_cache.clear()


class HoverToolButton(QToolButton):
    """
    A QToolButton that instantly switches icons on hover.

    This bypasses Qt's delayed hover state detection for QIcon modes
    by directly swapping pixmaps on mouse enter/leave events.
    """

    def __init__(self, icon_name: str, parent=None):
        super().__init__(parent)
        self._icon_name = icon_name
        self._normal_pixmap: Optional[QPixmap] = None
        self._hover_pixmap: Optional[QPixmap] = None
        self._current_size = QSize(24, 24)

        # Load both pixmaps
        self._load_pixmaps()

        # Set initial icon
        if self._normal_pixmap:
            self.setIcon(QIcon(self._normal_pixmap))

    def _load_pixmaps(self):
        """Load normal and hover pixmaps from cache."""
        self._normal_pixmap = load_icon_pixmap(self._icon_name, "normal")
        self._hover_pixmap = load_icon_pixmap(self._icon_name, "hover")

    def setIconSize(self, size: QSize):
        """Override to track current icon size."""
        super().setIconSize(size)
        self._current_size = size

    def enterEvent(self, event: QEvent):
        """Instantly switch to hover icon on mouse enter."""
        if self._hover_pixmap and self.isEnabled():
            scaled = self._hover_pixmap.scaled(
                self._current_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setIcon(QIcon(scaled))
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """Instantly switch back to normal icon on mouse leave."""
        if self._normal_pixmap:
            scaled = self._normal_pixmap.scaled(
                self._current_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setIcon(QIcon(scaled))
        super().leaveEvent(event)
