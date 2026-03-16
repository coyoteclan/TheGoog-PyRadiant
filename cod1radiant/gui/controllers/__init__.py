"""
Controller modules for MainWindow decomposition.

This package contains controller classes that handle specific functionality
domains, reducing the complexity of MainWindow by extracting operations
into dedicated modules.

Each controller has access to the MainWindow and manages its own set of
operations, events, and state.
"""

from .file_controller import FileController
from .edit_controller import EditController
from .view_controller import ViewController
from .brush_controller import BrushController

__all__ = [
    'FileController',
    'EditController',
    'ViewController',
    'BrushController',
]
