"""2D viewport using ModernGL for hardware-accelerated rendering."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtCore import Qt, QPoint, QPointF, pyqtSignal, QSettings
from PyQt6.QtGui import QWheelEvent, QMouseEvent, QResizeEvent, QKeyEvent, QColor
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

import moderngl

from ...config import COLORS, DEFAULT_GRID_SIZE, BRUSH_COLORS_2D
from ...render.bitmap_font import BitmapFont
from ...core import (
    events,
    SelectionChangedEvent,
    BrushGeometryModifiedEvent,
    FilterChangedEvent,
    DocumentLoadedEvent,
    ViewportRefreshEvent,
)
from ..tools import EditMode, EdgeTool, ResizeTool, BrushCreationTool, ClippingTool

from .grid_renderer import GridRenderer
from .geometry_builder import GeometryBuilder
from .overlay_renderer import OverlayRenderer
from .renderer import Renderer
from .input_handler import InputHandler
from .selection_handler import SelectionHandler

if TYPE_CHECKING:
    from ...core import MapDocument


class Viewport2DGL(QOpenGLWidget):
    """2D orthographic viewport using ModernGL for hardware-accelerated rendering."""

    # Signal emitted when brush geometry changes (after drag/edge edit ends)
    geometry_changed = pyqtSignal()

    # Signal emitted when user wants to create an entity at a position
    create_entity_requested = pyqtSignal(str, object)

    def __init__(self, document: "MapDocument", axis: str = 'xy', parent=None):
        super().__init__(parent)

        self.document = document
        self.axis = axis  # 'xy', 'xz', 'yz'
        self._settings = QSettings("CoD1Radiant", "Editor")

        # View parameters
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.zoom = 1.0
        self.grid_size = DEFAULT_GRID_SIZE

        # ModernGL context and resources
        self.ctx: moderngl.Context | None = None
        self.line_program: moderngl.Program | None = None
        self.point_program: moderngl.Program | None = None
        self.bitmap_font: BitmapFont | None = None

        # Visibility filters
        self._filters: dict[str, bool] = {}
        self._filtered_brushes: set[tuple[int, int]] = set()  # (entity_idx, brush_idx)
        self._filtered_entities: set[int] = set()
        self._filters_dirty = True

        # Interaction state
        self._panning = False
        self._last_mouse_pos = QPoint()
        self._right_click_pos: QPoint | None = None

        # Edit mode state
        self._edit_mode = EditMode.RESIZE

        # Initialize tools
        self._edge_tool = EdgeTool(self)
        self._resize_tool = ResizeTool(self)
        self._brush_creation_tool = BrushCreationTool(self)
        self._clipping_tool = ClippingTool(self)

        # Initialize modular components (created after init, used after initializeGL)
        self._grid_renderer: GridRenderer | None = None
        self._geometry_builder: GeometryBuilder | None = None
        self._overlay_renderer: OverlayRenderer | None = None
        self._renderer: Renderer | None = None
        self._input_handler: InputHandler | None = None
        self._selection_handler: SelectionHandler | None = None

        # Appearance
        self.setMinimumSize(200, 200)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        # Load colors from settings
        self._load_colors()

        # Subscribe to events
        events.subscribe(SelectionChangedEvent, self._on_selection_changed_event)
        events.subscribe(BrushGeometryModifiedEvent, self._on_brush_geometry_modified_event)
        events.subscribe(FilterChangedEvent, self._on_filter_changed_event)
        events.subscribe(DocumentLoadedEvent, self._on_document_loaded_event)
        events.subscribe(ViewportRefreshEvent, self._on_viewport_refresh_event)

    # =========================================================================
    # Event Handlers (Event-Bus)
    # =========================================================================

    def _on_selection_changed_event(self, event: SelectionChangedEvent) -> None:
        """Handle selection changes from the event bus."""
        if event.source == "viewport_2d":
            return
        self._edge_tool.on_selection_changed()
        self.update()

    def _on_brush_geometry_modified_event(self, event: BrushGeometryModifiedEvent) -> None:
        """Handle brush geometry modifications from the event bus."""
        self._notify_tools_geometry_changed()
        if self._geometry_builder:
            self._geometry_builder.mark_dirty()
        self.update()

    def _on_filter_changed_event(self, event: FilterChangedEvent) -> None:
        """Handle filter changes from the event bus."""
        self._filters = event.filters.copy()
        self._filters_dirty = True
        self._update_filtered_elements()
        self.update()

    def _on_document_loaded_event(self, event: DocumentLoadedEvent) -> None:
        """Handle document loaded event."""
        if self._geometry_builder:
            self._geometry_builder.mark_dirty()
        if self._grid_renderer:
            self._grid_renderer.mark_dirty()
        self._filters_dirty = True
        self._edge_tool.on_selection_changed()
        self.update()

    def _on_viewport_refresh_event(self, event: ViewportRefreshEvent) -> None:
        """Handle viewport refresh request."""
        if event.refresh_2d:
            if event.rebuild_geometry and self._geometry_builder:
                self._geometry_builder.mark_dirty()
            self.update()

    # =========================================================================
    # Settings and Colors
    # =========================================================================

    def _load_colors(self):
        """Load colors from settings or use defaults."""
        self._bg_color = self._get_color_tuple("colors/background2d", COLORS["background_2d"])
        self._grid_major_color = self._get_color_tuple("colors/gridMajor", COLORS["grid_major"])
        self._grid_minor_color = self._get_color_tuple("colors/gridMinor", COLORS["grid_minor"])
        self._selection_color_tuple = self._get_color_tuple("colors/selection", COLORS["selection"])
        self._brush_color = self._get_color_tuple("colors/brushOutline", COLORS["brush_outline"])

        self._selection_color = self._get_qcolor(self._selection_color_tuple)

        self._show_grid = self._settings.value("viewport/showGrid", True, type=bool)
        self._show_axis_labels = self._settings.value("viewport/showAxisLabels", True, type=bool)
        self._backface_culling_2d = self._settings.value("shader/backfaceCulling2d", True, type=bool)

        self._brush_colors_2d = {
            "structural": self._get_color_rgb("colors/brush2d/structural", BRUSH_COLORS_2D["structural"]),
            "detail": self._get_color_rgb("colors/brush2d/detail", BRUSH_COLORS_2D["detail"]),
            "weapon_clip": self._get_color_rgb("colors/brush2d/weaponClip", BRUSH_COLORS_2D["weapon_clip"]),
            "non_colliding": self._get_color_rgb("colors/brush2d/nonColliding", BRUSH_COLORS_2D["non_colliding"]),
            "brush": self._get_color_rgb("colors/brush2d/brush", BRUSH_COLORS_2D["brush"]),
            "curves": self._get_color_rgb("colors/brush2d/curves", BRUSH_COLORS_2D["curves"]),
            "terrain": self._get_color_rgb("colors/brush2d/terrain", BRUSH_COLORS_2D["terrain"]),
        }

    def _get_color_rgb(self, key: str, default: tuple) -> tuple[float, float, float]:
        """Get an RGB color tuple from settings."""
        value = self._settings.value(key)
        if value is not None:
            try:
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    return (float(value[0]), float(value[1]), float(value[2]))
                elif isinstance(value, str):
                    parts = value.strip("()[]").split(",")
                    if len(parts) >= 3:
                        return (float(parts[0]), float(parts[1]), float(parts[2]))
            except (ValueError, TypeError, IndexError):
                pass
        return default

    def _get_color_tuple(self, key: str, default: tuple) -> tuple:
        """Get a color tuple from settings."""
        value = self._settings.value(key)
        if value is not None:
            try:
                if isinstance(value, (list, tuple)) and len(value) >= 3:
                    r, g, b = float(value[0]), float(value[1]), float(value[2])
                    a = float(value[3]) if len(value) > 3 else 1.0
                    return (r, g, b, a)
                elif isinstance(value, str):
                    parts = value.strip("()[]").split(",")
                    if len(parts) >= 3:
                        r, g, b = float(parts[0]), float(parts[1]), float(parts[2])
                        a = float(parts[3]) if len(parts) > 3 else 1.0
                        return (r, g, b, a)
            except (ValueError, TypeError, IndexError):
                pass
        return default

    def _get_qcolor(self, color_tuple: tuple) -> QColor:
        """Convert color tuple to QColor."""
        r, g, b = color_tuple[0], color_tuple[1], color_tuple[2]
        a = color_tuple[3] if len(color_tuple) > 3 else 1.0
        return QColor.fromRgbF(r, g, b, a)

    def reload_settings(self):
        """Reload settings (call after preferences change)."""
        self._load_colors()
        if self._grid_renderer:
            self._grid_renderer.mark_dirty()
        if self._geometry_builder:
            self._geometry_builder.mark_dirty()
        self.update()

    # =========================================================================
    # Public API
    # =========================================================================

    def set_document(self, document: "MapDocument"):
        """Set the document to display."""
        self.document = document
        if self._geometry_builder:
            self._geometry_builder.mark_dirty()
        self.update()

    def set_grid_size(self, size: int):
        """Set the grid size."""
        self.grid_size = size
        if self._grid_renderer:
            self._grid_renderer.mark_dirty()
        self.update()

    def set_axis(self, axis: str):
        """Set the view axis ('xy', 'xz', or 'yz')."""
        if axis in ('xy', 'xz', 'yz'):
            self.axis = axis
            self._notify_tools_geometry_changed()
            if self._geometry_builder:
                self._geometry_builder.mark_dirty()
            if self.document.selection.selected_brushes:
                self.center_on_selection()
            else:
                self.update()

    def notify_geometry_changed(self):
        """Notify that brush geometry has changed externally."""
        self._notify_tools_geometry_changed()
        if self._geometry_builder:
            self._geometry_builder.mark_dirty()
        self.update()

    def notify_selection_changed(self):
        """Notify that selection has changed."""
        self._edge_tool.on_selection_changed()
        self.update()

    def set_filters(self, filters: dict[str, bool]):
        """Set visibility filters and update rendering."""
        self._filters = filters.copy()
        self._filters_dirty = True
        self._update_filtered_elements()
        self.update()

    def _update_filtered_elements(self):
        """Update the sets of visible brushes and entities based on filters."""
        from ..filter_panel import BrushFilterMatcher, EntityFilterMatcher

        if not self._filters_dirty:
            return

        self._filtered_brushes.clear()
        self._filtered_entities.clear()

        if not self._filters:
            # No filters - show all
            for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
                self._filtered_brushes.add((entity_idx, brush_idx))
            for entity_idx in range(len(self.document.entities)):
                self._filtered_entities.add(entity_idx)
            self._filters_dirty = False
            return

        # Apply filters
        for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
            if BrushFilterMatcher.should_show_brush(brush, self._filters):
                self._filtered_brushes.add((entity_idx, brush_idx))

        for entity_idx, entity in enumerate(self.document.entities):
            if EntityFilterMatcher.should_show_entity(entity, self._filters):
                self._filtered_entities.add(entity_idx)

        self._filters_dirty = False

    def _notify_tools_geometry_changed(self):
        """Internal: notify all tools that geometry has changed."""
        self._edge_tool.on_selection_changed()

    # =========================================================================
    # Coordinate Conversion
    # =========================================================================

    def world_to_screen(self, wx: float, wy: float) -> QPointF:
        """Convert world coordinates to screen coordinates."""
        cx = self.width() / 2
        cy = self.height() / 2
        sx = cx + (wx - self.offset_x) * self.zoom
        sy = cy - (wy - self.offset_y) * self.zoom
        return QPointF(sx, sy)

    def screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Convert screen coordinates to world coordinates."""
        w, h = self.width(), self.height()
        if w == 0 or h == 0:
            w, h = 800, 600
        cx = w / 2
        cy = h / 2
        wx = (sx - cx) / self.zoom + self.offset_x
        wy = -(sy - cy) / self.zoom + self.offset_y
        return (wx, wy)

    def _get_axes(self) -> tuple[int, int]:
        """Get the world axis indices for this viewport."""
        if self.axis == 'xy':
            return (0, 1)
        elif self.axis == 'xz':
            return (0, 2)
        else:
            return (1, 2)

    def _get_axis_labels(self) -> tuple[str, str]:
        """Get the axis labels for this viewport."""
        if self.axis == 'xy':
            return ('X', 'Y')
        elif self.axis == 'xz':
            return ('X', 'Z')
        else:
            return ('Y', 'Z')

    def _get_view_name(self) -> str:
        """Get the display name for the current view."""
        if self.axis == 'xy':
            return "Top"
        elif self.axis == 'xz':
            return "Front"
        else:
            return "Side"

    # =========================================================================
    # OpenGL Initialization
    # =========================================================================

    def initializeGL(self):
        """Initialize OpenGL context and resources."""
        try:
            self.ctx = moderngl.create_context()
            print(f"2D Viewport OpenGL initialized: {self.ctx.info['GL_RENDERER']}")

            self._gl_context_id = id(self.ctx)
            print(f"  Context ID: {self._gl_context_id}")

            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

            self._load_shaders()

            self.bitmap_font = BitmapFont(self.ctx, font_name="arial", font_size=12)

            # Initialize modular components now that context exists
            self._grid_renderer = GridRenderer(self)
            self._geometry_builder = GeometryBuilder(self)
            self._overlay_renderer = OverlayRenderer(self)
            self._renderer = Renderer(self)
            self._input_handler = InputHandler(self)
            self._selection_handler = SelectionHandler(self)

        except Exception as e:
            print(f"2D Viewport OpenGL initialization error: {e}")
            import traceback
            traceback.print_exc()
            self.ctx = None

    def _load_shaders(self):
        """Load shader programs."""
        shader_dir = Path(__file__).parent.parent.parent / "render" / "shaders"

        line_vert = (shader_dir / "line_2d.vert").read_text()
        line_frag = (shader_dir / "line_2d.frag").read_text()
        self.line_program = self.ctx.program(
            vertex_shader=line_vert,
            fragment_shader=line_frag
        )

        point_vert = (shader_dir / "point_2d.vert").read_text()
        point_frag = (shader_dir / "point_2d.frag").read_text()
        self.point_program = self.ctx.program(
            vertex_shader=point_vert,
            fragment_shader=point_frag
        )

    def _create_orthographic_projection(self) -> np.ndarray:
        """Create orthographic projection matrix for 2D rendering."""
        w, h = self.width(), self.height()
        if w == 0 or h == 0:
            w, h = 1, 1

        left = -w / 2
        right = w / 2
        bottom = -h / 2
        top = h / 2
        near = -1.0
        far = 1.0

        projection = np.array([
            [2.0 / (right - left), 0, 0, 0],
            [0, 2.0 / (top - bottom), 0, 0],
            [0, 0, -2.0 / (far - near), 0],
            [-(right + left) / (right - left), -(top + bottom) / (top - bottom), -(far + near) / (far - near), 1]
        ], dtype='f4')

        return projection

    # =========================================================================
    # Rendering
    # =========================================================================

    def resizeGL(self, width: int, height: int):
        """Handle resize."""
        if self.ctx:
            self.ctx.viewport = (0, 0, width, height)
        if self._grid_renderer:
            self._grid_renderer.mark_dirty()

    def paintGL(self):
        """Render the 2D viewport."""
        if self.ctx is None:
            return

        try:
            fbo = self.ctx.detect_framebuffer()
            fbo.use()

            w, h = self.width(), self.height()
            if w > 0 and h > 0:
                self.ctx.viewport = (0, 0, w, h)

            self.ctx.disable(moderngl.DEPTH_TEST)

            bg = self._bg_color
            self.ctx.clear(bg[0], bg[1], bg[2], bg[3] if len(bg) > 3 else 1.0)

            # Rebuild grid if needed
            if self._grid_renderer and self._grid_renderer.needs_rebuild():
                self._grid_renderer.rebuild()

            # Rebuild geometry if needed
            if self._geometry_builder and self._geometry_builder.is_dirty():
                self._geometry_builder.rebuild()

            # Get projection matrix
            projection = self._create_orthographic_projection()

            # Set common uniforms
            if self.line_program:
                self.line_program['u_projection'].write(projection.tobytes())
                self.line_program['u_offset'].value = (self.offset_x, self.offset_y)
                self.line_program['u_zoom'].value = self.zoom

            # Draw grid
            if self._show_grid and self._grid_renderer:
                self._grid_renderer.draw()

            # Draw brushes and patches
            if self._renderer:
                self._renderer.draw_brushes()
                self._renderer.draw_entities(projection)

            # Draw tool overlays
            if self._overlay_renderer:
                self._overlay_renderer.draw_tool_overlays()
                self._overlay_renderer.draw_text_overlays()

        except Exception as e:
            print(f"2D Viewport render error: {e}")
            import traceback
            traceback.print_exc()

    # =========================================================================
    # Input Events
    # =========================================================================

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for zooming."""
        if self._input_handler:
            self._input_handler.handle_wheel(event)

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if self._input_handler:
            self._input_handler.handle_mouse_press(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._input_handler:
            self._input_handler.handle_mouse_release(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        if self._input_handler:
            self._input_handler.handle_mouse_move(event)

    def event(self, event) -> bool:
        """Override to intercept Tab key before focus navigation."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Tab:
                if self._input_handler and self._input_handler.handle_tab_key():
                    return True
        return super().event(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press events."""
        if self._input_handler:
            if not self._input_handler.handle_key_press(event):
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)

    # =========================================================================
    # View Navigation
    # =========================================================================

    def center_on_origin(self):
        """Center the view on the origin."""
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.update()

    def center_on_selection(self):
        """Center the view on the current selection."""
        from ...core import get_brush_bounds

        selected = self.document.selection.selected_brushes
        if not selected:
            return

        axis_h, axis_v = self._get_axes()

        min_vals = [float('inf'), float('inf')]
        max_vals = [float('-inf'), float('-inf')]

        for entity_idx, brush_idx in selected:
            brush = self.document.get_brush(entity_idx, brush_idx)
            if brush is None:
                continue
            bounds = get_brush_bounds(brush)
            if bounds:
                b_min, b_max = bounds
                b_min_arr = (b_min.x, b_min.y, b_min.z)
                b_max_arr = (b_max.x, b_max.y, b_max.z)
                min_vals[0] = min(min_vals[0], b_min_arr[axis_h])
                min_vals[1] = min(min_vals[1], b_min_arr[axis_v])
                max_vals[0] = max(max_vals[0], b_max_arr[axis_h])
                max_vals[1] = max(max_vals[1], b_max_arr[axis_v])

        if min_vals[0] == float('inf'):
            return

        self.offset_x = (min_vals[0] + max_vals[0]) / 2
        self.offset_y = (min_vals[1] + max_vals[1]) / 2
        self.update()

    def fit_to_map(self):
        """Fit the view to show the entire map."""
        from ...core import get_brush_bounds

        axis_h, axis_v = self._get_axes()

        min_vals = [float('inf'), float('inf')]
        max_vals = [float('-inf'), float('-inf')]

        for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
            bounds = get_brush_bounds(brush)
            if bounds:
                b_min, b_max = bounds
                b_min_arr = (b_min.x, b_min.y, b_min.z)
                b_max_arr = (b_max.x, b_max.y, b_max.z)
                min_vals[0] = min(min_vals[0], b_min_arr[axis_h])
                min_vals[1] = min(min_vals[1], b_min_arr[axis_v])
                max_vals[0] = max(max_vals[0], b_max_arr[axis_h])
                max_vals[1] = max(max_vals[1], b_max_arr[axis_v])

        if min_vals[0] == float('inf'):
            return

        self.offset_x = (min_vals[0] + max_vals[0]) / 2
        self.offset_y = (min_vals[1] + max_vals[1]) / 2

        world_width = max_vals[0] - min_vals[0]
        world_height = max_vals[1] - min_vals[1]

        if world_width > 0 and world_height > 0:
            margin = 1.2
            zoom_x = self.width() / (world_width * margin)
            zoom_y = self.height() / (world_height * margin)
            self.zoom = min(zoom_x, zoom_y)

        self.update()

    # =========================================================================
    # Helpers
    # =========================================================================

    def _notify_3d_viewport(self):
        """Notify 3D viewport to update."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'viewport_3d'):
                parent.viewport_3d.update()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None

    def _rebuild_3d_geometry(self):
        """Tell the 3D viewport to rebuild geometry."""
        parent = self.parent()
        while parent:
            if hasattr(parent, 'viewport_3d'):
                parent.viewport_3d._rebuild_moved_brushes()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None
