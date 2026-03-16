"""Settings dialog tab modules."""

from .general_tab import GeneralTab
from .viewport_tab import ViewportTab
from .colors_tab import ColorsTab
from .shader_tab import ShaderTab
from .keybindings_tab import KeybindingsTab
from .color_utils import ColorButton, rgba_to_qcolor, rgb_to_qcolor, qcolor_to_rgba, qcolor_to_rgb

__all__ = [
    "GeneralTab",
    "ViewportTab",
    "ColorsTab",
    "ShaderTab",
    "KeybindingsTab",
    "ColorButton",
    "rgba_to_qcolor",
    "rgb_to_qcolor",
    "qcolor_to_rgba",
    "qcolor_to_rgb",
]
