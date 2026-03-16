"""Menu bar creation for the main window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtGui import QAction, QKeySequence

if TYPE_CHECKING:
    from ..main_window import MainWindow


def create_menus(window: "MainWindow") -> None:
    """Create the menu bar and menus for the main window.

    Args:
        window: The main window instance
    """
    menubar = window.menuBar()

    # File menu
    _create_file_menu(window, menubar)

    # Edit menu
    _create_edit_menu(window, menubar)

    # View menu
    _create_view_menu(window, menubar)

    # Brush menu
    _create_brush_menu(window, menubar)

    # Tools menu
    _create_tools_menu(window, menubar)

    # Help menu
    _create_help_menu(window, menubar)


def _create_file_menu(window: "MainWindow", menubar) -> None:
    """Create the File menu."""
    file_menu = menubar.addMenu("&File")

    new_action = QAction("&New", window)
    new_action.setShortcut(QKeySequence.StandardKey.New)
    new_action.triggered.connect(window._on_new)
    file_menu.addAction(new_action)

    open_action = QAction("&Open...", window)
    open_action.setShortcut(QKeySequence.StandardKey.Open)
    open_action.triggered.connect(window._on_open)
    file_menu.addAction(open_action)

    file_menu.addSeparator()

    save_action = QAction("&Save", window)
    save_action.setShortcut(QKeySequence.StandardKey.Save)
    save_action.triggered.connect(window._on_save)
    file_menu.addAction(save_action)

    save_as_action = QAction("Save &As...", window)
    save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
    save_as_action.triggered.connect(window._on_save_as)
    file_menu.addAction(save_as_action)

    file_menu.addSeparator()

    # Recent files submenu
    window.recent_menu = file_menu.addMenu("Recent Files")
    window._update_recent_menu()

    file_menu.addSeparator()

    exit_action = QAction("E&xit", window)
    exit_action.setShortcut(QKeySequence.StandardKey.Quit)
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)


def _create_edit_menu(window: "MainWindow", menubar) -> None:
    """Create the Edit menu."""
    edit_menu = menubar.addMenu("&Edit")

    undo_action = QAction("&Undo", window)
    undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    undo_action.triggered.connect(window._on_undo)
    edit_menu.addAction(undo_action)

    redo_action = QAction("&Redo", window)
    redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    redo_action.triggered.connect(window._on_redo)
    edit_menu.addAction(redo_action)

    edit_menu.addSeparator()

    copy_action = QAction("&Copy", window)
    copy_action.setShortcut(QKeySequence.StandardKey.Copy)
    edit_menu.addAction(copy_action)

    paste_action = QAction("&Paste", window)
    paste_action.setShortcut(QKeySequence.StandardKey.Paste)
    edit_menu.addAction(paste_action)

    delete_action = QAction("&Delete", window)
    delete_action.setShortcut(QKeySequence.StandardKey.Delete)
    delete_action.triggered.connect(window._on_delete)
    edit_menu.addAction(delete_action)

    edit_menu.addSeparator()

    select_all_action = QAction("Select &All", window)
    select_all_action.setShortcut(QKeySequence.StandardKey.SelectAll)
    edit_menu.addAction(select_all_action)

    deselect_action = QAction("&Deselect All", window)
    deselect_action.setShortcut(QKeySequence("Escape"))
    deselect_action.triggered.connect(window._on_deselect)
    edit_menu.addAction(deselect_action)

    edit_menu.addSeparator()

    preferences_action = QAction("&Preferences...", window)
    preferences_action.setShortcut(QKeySequence("Ctrl+,"))
    preferences_action.triggered.connect(window._on_preferences)
    edit_menu.addAction(preferences_action)


def _create_view_menu(window: "MainWindow", menubar) -> None:
    """Create the View menu."""
    view_menu = menubar.addMenu("&View")

    # 2D View switching
    view_menu.addAction("Cycle 2D View (Ctrl+Tab)")
    view_menu.addSeparator()

    top_view_action = QAction("&Top (XY)", window)
    top_view_action.setShortcut(QKeySequence("Ctrl+1"))
    top_view_action.triggered.connect(lambda: window._set_view_mode(0))
    view_menu.addAction(top_view_action)

    front_view_action = QAction("&Front (XZ)", window)
    front_view_action.setShortcut(QKeySequence("Ctrl+2"))
    front_view_action.triggered.connect(lambda: window._set_view_mode(1))
    view_menu.addAction(front_view_action)

    side_view_action = QAction("&Side (YZ)", window)
    side_view_action.setShortcut(QKeySequence("Ctrl+3"))
    side_view_action.triggered.connect(lambda: window._set_view_mode(2))
    view_menu.addAction(side_view_action)

    view_menu.addSeparator()

    grid_larger_action = QAction("Grid &Larger", window)
    grid_larger_action.setShortcut(QKeySequence("]"))
    grid_larger_action.triggered.connect(window._on_grid_larger)
    view_menu.addAction(grid_larger_action)

    grid_smaller_action = QAction("Grid &Smaller", window)
    grid_smaller_action.setShortcut(QKeySequence("["))
    grid_smaller_action.triggered.connect(window._on_grid_smaller)
    view_menu.addAction(grid_smaller_action)

    view_menu.addSeparator()

    zoom_in_action = QAction("Zoom &In", window)
    zoom_in_action.setShortcut(QKeySequence("Ctrl++"))
    view_menu.addAction(zoom_in_action)

    zoom_out_action = QAction("Zoom &Out", window)
    zoom_out_action.setShortcut(QKeySequence("Ctrl+-"))
    view_menu.addAction(zoom_out_action)

    view_menu.addSeparator()

    # Panels submenu (will be populated after docks are created)
    window.panels_menu = view_menu.addMenu("&Panels")


def _create_brush_menu(window: "MainWindow", menubar) -> None:
    """Create the Brush menu."""
    brush_menu = menubar.addMenu("&Brush")

    create_block_action = QAction("Create &Block", window)
    create_block_action.setShortcut(QKeySequence("Ctrl+B"))
    create_block_action.triggered.connect(lambda: window._create_primitive("block"))
    brush_menu.addAction(create_block_action)

    brush_menu.addSeparator()

    create_cylinder_action = QAction("Create C&ylinder", window)
    create_cylinder_action.triggered.connect(lambda: window._create_primitive("cylinder"))
    brush_menu.addAction(create_cylinder_action)

    create_cone_action = QAction("Create C&one", window)
    create_cone_action.triggered.connect(lambda: window._create_primitive("cone"))
    brush_menu.addAction(create_cone_action)

    create_wedge_action = QAction("Create &Wedge", window)
    create_wedge_action.triggered.connect(lambda: window._create_primitive("wedge"))
    brush_menu.addAction(create_wedge_action)

    create_spike_action = QAction("Create &Spike", window)
    create_spike_action.triggered.connect(lambda: window._create_primitive("spike"))
    brush_menu.addAction(create_spike_action)


def _create_tools_menu(window: "MainWindow", menubar) -> None:
    """Create the Tools menu."""
    tools_menu = menubar.addMenu("&Tools")

    texture_browser_action = QAction("&Texture Browser", window)
    texture_browser_action.setShortcut(QKeySequence("T"))
    texture_browser_action.triggered.connect(window.show_texture_browser)
    tools_menu.addAction(texture_browser_action)

    surface_inspector_action = QAction("&Surface Inspector", window)
    surface_inspector_action.setShortcut(QKeySequence("S"))
    tools_menu.addAction(surface_inspector_action)

    entity_list_action = QAction("&Entity List", window)
    entity_list_action.setShortcut(QKeySequence("L"))
    tools_menu.addAction(entity_list_action)


def _create_help_menu(window: "MainWindow", menubar) -> None:
    """Create the Help menu."""
    help_menu = menubar.addMenu("&Help")

    about_action = QAction("&About", window)
    about_action.triggered.connect(window._on_about)
    help_menu.addAction(about_action)
