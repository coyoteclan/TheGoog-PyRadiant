"""Toolbar creation for the main window."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import QToolBar

from ..icon_loader import HoverToolButton, load_icon_pixmap, load_toolbar_icon

if TYPE_CHECKING:
    from ..main_window import MainWindow


def create_toolbars(window: "MainWindow") -> None:
    """Create all toolbars for the main window.

    Args:
        window: The main window instance
    """
    # Get icon size based on UI density setting
    ui_density = window._settings.value("colors/uiDensity", "semi_compact", type=str)
    if ui_density == "compact":
        icon_size = QSize(20, 20)
    elif ui_density == "normal":
        icon_size = QSize(32, 32)
    else:  # semi_compact (default)
        icon_size = QSize(24, 24)

    # Store toolbars for later icon size updates
    window._toolbars: list[QToolBar] = []

    # Create all toolbars
    _create_main_toolbar(window, icon_size)
    _create_tools_toolbar(window, icon_size)
    _create_selection_toolbar(window, icon_size)
    _create_texture_toolbar(window, icon_size)
    _create_view_toolbar(window, icon_size)
    _create_fx_toolbar(window, icon_size)
    _create_gizmo_toolbar(window, icon_size)
    _create_filter_toolbar(window, icon_size)
    _create_entity_toolbar(window, icon_size)
    _create_patch_toolbar(window, icon_size)
    _create_vertex_toolbar(window, icon_size)


def _create_main_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the main toolbar with file operations."""
    toolbar = QToolBar("Main")
    toolbar.setObjectName("MainToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "open", "Open", "Open Map (Ctrl+O)")
    add_toolbar_action(window, toolbar, "save", "Save", "Save Map (Ctrl+S)")
    add_toolbar_action(window, toolbar, "save_as", "Save As", "Save Map As (Ctrl+Shift+S)")
    toolbar.addSeparator()
    add_toolbar_action(window, toolbar, "duplicate_reload", "Reload", "Reload Map")


def _create_tools_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the tools toolbar with brush/edit tools."""
    toolbar = QToolBar("Tools")
    toolbar.setObjectName("ToolsToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    # Brush tools
    add_toolbar_action(window, toolbar, "toolbox_brush", "Brush", "Brush Tool")
    add_toolbar_action(window, toolbar, "toolbox_patch", "Patch", "Patch Tool")
    add_toolbar_action(window, toolbar, "clipper", "Clip", "Clipper Tool")
    toolbar.addSeparator()

    # CSG operations
    add_toolbar_action(window, toolbar, "csg_hollow", "Hollow", "CSG Hollow")
    add_toolbar_action(window, toolbar, "csg_merge", "Merge", "CSG Merge")
    toolbar.addSeparator()

    # Transform tools
    add_toolbar_action(window, toolbar, "free_rotate", "Rotate", "Free Rotate")
    add_toolbar_action(window, toolbar, "free_scale", "Scale", "Free Scale")
    toolbar.addSeparator()

    # Flip tools
    add_toolbar_action(window, toolbar, "flip_x", "Flip X", "Flip X Axis")
    add_toolbar_action(window, toolbar, "flip_y", "Flip Y", "Flip Y Axis")
    add_toolbar_action(window, toolbar, "flip_z", "Flip Z", "Flip Z Axis")
    toolbar.addSeparator()

    # Rotate axis tools
    add_toolbar_action(window, toolbar, "rotate_x", "Rot X", "Rotate X Axis")
    add_toolbar_action(window, toolbar, "rotate_y", "Rot Y", "Rotate Y Axis")
    add_toolbar_action(window, toolbar, "rotate_z", "Rot Z", "Rotate Z Axis")


def _create_selection_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the selection toolbar."""
    toolbar = QToolBar("Selection")
    toolbar.setObjectName("SelectionToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "select_inside", "Inside", "Select Inside")
    add_toolbar_action(window, toolbar, "select_touching", "Touching", "Select Touching")
    add_toolbar_action(window, toolbar, "select_complete_tall", "Complete", "Select Complete Tall")
    add_toolbar_action(window, toolbar, "select_partial_tall", "Partial", "Select Partial Tall")
    toolbar.addSeparator()
    add_toolbar_action(window, toolbar, "cycle_xyz", "Cycle XYZ", "Cycle XYZ Axis")
    add_toolbar_action(window, toolbar, "cycle_layer", "Cycle Layer", "Cycle Layer")


def _create_texture_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the texture toolbar."""
    toolbar = QToolBar("Texture")
    toolbar.setObjectName("TextureToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "surface_inspector", "Surface", "Surface Inspector")
    toolbar.addSeparator()
    add_toolbar_action(window, toolbar, "texflip_x", "Flip U", "Flip Texture U")
    add_toolbar_action(window, toolbar, "texflip_y", "Flip V", "Flip Texture V")
    add_toolbar_action(window, toolbar, "texflip_90", "Rot 90", "Rotate Texture 90")


def _create_view_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the view toolbar."""
    toolbar = QToolBar("View")
    toolbar.setObjectName("ViewToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    # Filter/Layers
    add_toolbar_action(window, toolbar, "filter", "Filter", "Filter Settings")
    add_toolbar_action(window, toolbar, "layers", "Layers", "Layers")
    toolbar.addSeparator()

    # Entity/Patch display
    add_toolbar_action(window, toolbar, "entity_properties", "Entities", "Entity Properties")
    add_toolbar_action(window, toolbar, "show_entities_as", "Entity Mode", "Show Entities As")
    add_toolbar_action(window, toolbar, "show_patches_as", "Patch Mode", "Show Patches As")
    toolbar.addSeparator()

    # View modes
    add_toolbar_action(window, toolbar, "gameview", "Game View", "Toggle Game View")
    add_toolbar_action(window, toolbar, "lightpreview", "Light Preview", "Light Preview")
    add_toolbar_action(window, toolbar, "sunpreview", "Sun Preview", "Sun Preview")
    toolbar.addSeparator()

    # Camera
    add_toolbar_action(window, toolbar, "camera_movement", "Camera", "Camera Movement Mode")
    add_toolbar_action(window, toolbar, "physx_movement", "PhysX", "PhysX Movement Mode")
    add_toolbar_action(window, toolbar, "cubic_clip", "Cubic Clip", "Cubic Clipping")
    toolbar.addSeparator()

    # View toggles
    add_toolbar_action(window, toolbar, "toggle_bsp", "BSP", "Toggle BSP View", checkable=True)
    add_toolbar_action(window, toolbar, "toggle_draw_surfs_portal", "Portals", "Toggle Portal Surfaces", checkable=True)
    add_toolbar_action(window, toolbar, "toggle_radiant_world", "World", "Toggle Radiant World", checkable=True)
    toolbar.addSeparator()

    # Sun/Lighting settings
    add_toolbar_action(window, toolbar, "fakesun_settings", "Sun Settings", "Fake Sun Settings")
    add_toolbar_action(window, toolbar, "fakesun_fog", "Fog", "Fake Sun Fog Settings")
    add_toolbar_action(window, toolbar, "filmtweaks", "Film Tweaks", "Film Tweaks Settings")


def _create_fx_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the FX toolbar for effects preview."""
    toolbar = QToolBar("FX")
    toolbar.setObjectName("FXToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "fx_edit", "Edit FX", "Edit Effects")
    add_toolbar_action(window, toolbar, "fx_play", "Play", "Play Effects")
    add_toolbar_action(window, toolbar, "fx_pause", "Pause", "Pause Effects")
    add_toolbar_action(window, toolbar, "fx_stop", "Stop", "Stop Effects")
    add_toolbar_action(window, toolbar, "fx_repeat", "Repeat", "Repeat Effects", checkable=True)


def _create_gizmo_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the gizmo toolbar."""
    toolbar = QToolBar("Gizmo")
    toolbar.setObjectName("GizmoToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "guizmo_enable", "Gizmo", "Enable Gizmo", checkable=True)
    add_toolbar_action(window, toolbar, "guizmo_world_local", "World/Local", "Toggle World/Local", checkable=True)
    add_toolbar_action(window, toolbar, "guizmo_grid_snapping", "Snap", "Grid Snapping", checkable=True)
    add_toolbar_action(window, toolbar, "guizmo_brush_mode", "Brush Mode", "Gizmo Brush Mode", checkable=True)


def _create_filter_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the filter toolbar for selection filters."""
    toolbar = QToolBar("Selection Filter")
    toolbar.setObjectName("FilterToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "dont_select_curve", "No Curves", "Don't Select Curves", checkable=True)
    add_toolbar_action(window, toolbar, "dont_select_models", "No Models", "Don't Select Models", checkable=True)
    add_toolbar_action(window, toolbar, "dont_select_entities", "No Entities", "Don't Select Entities", checkable=True)
    add_toolbar_action(window, toolbar, "dont_select_sky", "No Sky", "Don't Select Sky", checkable=True)
    toolbar.addSeparator()

    # Lock axes
    add_toolbar_action(window, toolbar, "lock_x", "Lock X", "Lock X Axis", checkable=True)
    add_toolbar_action(window, toolbar, "lock_y", "Lock Y", "Lock Y Axis", checkable=True)
    add_toolbar_action(window, toolbar, "lock_z", "Lock Z", "Lock Z Axis", checkable=True)


def _create_entity_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the entity toolbar."""
    toolbar = QToolBar("Entity")
    toolbar.setObjectName("EntityToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "drop_entities_floor", "Drop Floor", "Drop Entities to Floor")
    add_toolbar_action(window, toolbar, "drop_entities_floor_relative", "Drop Relative", "Drop Entities to Floor (Relative)")
    toolbar.addSeparator()
    add_toolbar_action(window, toolbar, "plant_models", "Plant", "Plant Models")
    add_toolbar_action(window, toolbar, "plant_orient_to_floor", "Orient Floor", "Plant Orient to Floor")
    add_toolbar_action(window, toolbar, "plant_force_drop_height", "Drop Height", "Force Drop Height")


def _create_patch_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the patch toolbar."""
    toolbar = QToolBar("Patch")
    toolbar.setObjectName("PatchToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "patch_cap_bevel", "Cap Bevel", "Patch Cap Bevel")
    add_toolbar_action(window, toolbar, "patch_cap_endcap", "Cap Endcap", "Patch Cap Endcap")
    add_toolbar_action(window, toolbar, "cycle_patch_edge_direction", "Edge Dir", "Cycle Patch Edge Direction")
    add_toolbar_action(window, toolbar, "redisperse_patch_points", "Redisperse", "Redisperse Patch Points")


def _create_vertex_toolbar(window: "MainWindow", icon_size: QSize) -> None:
    """Create the vertex toolbar."""
    toolbar = QToolBar("Vertex")
    toolbar.setObjectName("VertexToolbar")
    toolbar.setIconSize(icon_size)
    window.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)
    window._toolbars.append(toolbar)

    add_toolbar_action(window, toolbar, "toggle_lock_vertices_mode", "Lock Verts", "Lock Vertices Mode", checkable=True)
    add_toolbar_action(window, toolbar, "toggle_unlock_vertices_mode", "Unlock Verts", "Unlock Vertices Mode", checkable=True)
    add_toolbar_action(window, toolbar, "select_drill_down_vertices", "Drill Down", "Select Drill Down Vertices")
    add_toolbar_action(window, toolbar, "tolerant_weld", "Weld", "Tolerant Weld")
    add_toolbar_action(window, toolbar, "weld_equal_patches_move", "Weld Patches", "Weld Equal Patches")


def add_toolbar_action(
    window: "MainWindow",
    toolbar: QToolBar,
    icon_name: str,
    text: str,
    tooltip: str,
    checkable: bool = False
) -> QAction:
    """Add an action to a toolbar with an icon using HoverToolButton.

    Args:
        window: The main window instance
        toolbar: The toolbar to add the action to
        icon_name: Name of the icon file (without .dds extension)
        text: Text label for the action
        tooltip: Tooltip text
        checkable: Whether the action is checkable

    Returns:
        The created QAction
    """
    # Check if icon exists
    normal_pixmap = load_icon_pixmap(icon_name, "normal")

    if normal_pixmap:
        # Use custom HoverToolButton for instant hover response
        button = HoverToolButton(icon_name)
        button.setIconSize(toolbar.iconSize())
        button.setToolTip(tooltip)
        button.setCheckable(checkable)
        action = toolbar.addWidget(button)
        # Store reference to button for later icon size updates
        action.setData(button)
    else:
        # Fallback to text-only action
        action = toolbar.addAction(text)
        action.setToolTip(tooltip)
        if checkable:
            action.setCheckable(True)

    return action


def update_toolbar_icon_size(window: "MainWindow") -> None:
    """Update toolbar icon sizes based on UI density setting.

    Args:
        window: The main window instance
    """
    ui_density = window._settings.value("colors/uiDensity", "semi_compact", type=str)
    if ui_density == "compact":
        icon_size = QSize(20, 20)
    elif ui_density == "normal":
        icon_size = QSize(32, 32)
    else:  # semi_compact (default)
        icon_size = QSize(24, 24)

    if hasattr(window, '_toolbars'):
        for toolbar in window._toolbars:
            toolbar.setIconSize(icon_size)
            # Update HoverToolButton sizes
            for action in toolbar.actions():
                widget = action.data()
                if isinstance(widget, HoverToolButton):
                    widget.setIconSize(icon_size)
