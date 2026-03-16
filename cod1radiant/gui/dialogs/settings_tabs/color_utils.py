"""Color utility functions and widgets for settings dialog."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QPushButton, QColorDialog


def rgba_to_qcolor(rgba: tuple) -> QColor:
    """Convert normalized RGBA tuple to QColor."""
    return QColor.fromRgbF(rgba[0], rgba[1], rgba[2], rgba[3] if len(rgba) > 3 else 1.0)


def rgb_to_qcolor(rgb: tuple) -> QColor:
    """Convert normalized RGB tuple to QColor (no alpha)."""
    return QColor.fromRgbF(rgb[0], rgb[1], rgb[2], 1.0)


def qcolor_to_rgba(color: QColor) -> tuple:
    """Convert QColor to normalized RGBA tuple."""
    return (color.redF(), color.greenF(), color.blueF(), color.alphaF())


def qcolor_to_rgb(color: QColor) -> tuple:
    """Convert QColor to normalized RGB tuple (no alpha)."""
    return (color.redF(), color.greenF(), color.blueF())


class ColorButton(QPushButton):
    """A button that displays and allows selecting a color."""

    color_changed = pyqtSignal(QColor)

    def __init__(self, color: QColor = None, parent=None):
        super().__init__(parent)
        self._color = color or QColor(255, 255, 255)
        self.setFixedSize(60, 24)
        self._update_style()
        self.clicked.connect(self._on_clicked)

    def _update_style(self):
        """Update button background to show current color."""
        self.setStyleSheet(
            f"background-color: {self._color.name()}; "
            f"border: 1px solid palette(mid); border-radius: 3px;"
        )

    def _on_clicked(self):
        """Open color picker dialog."""
        dialog = QColorDialog(self._color)
        dialog.setWindowTitle("Select Color")
        dialog.setOption(QColorDialog.ColorDialogOption.ShowAlphaChannel, True)

        if dialog.exec() == QColorDialog.DialogCode.Accepted:
            color = dialog.currentColor()
            if color.isValid():
                self._color = color
                self._update_style()
                self.color_changed.emit(color)

    def color(self) -> QColor:
        """Get the current color."""
        return self._color

    def setColor(self, color: QColor):
        """Set the current color."""
        self._color = color
        self._update_style()
