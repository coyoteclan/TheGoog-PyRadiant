"""3D OpenGL viewport using ModernGL."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from PyQt6.QtOpenGLWidgets import QOpenGLWidget

import moderngl

from ...render.camera import Camera
from ...render.frustum import FrustumCuller
from ...render.batch_renderer import BatchedBrushRenderer
from ...render.instanced_renderer import InstancedMarkerRenderer
from ...core.octree import BrushOctree
from ...core import (
    events,
    SelectionChangedEvent,
    BrushGeometryModifiedEvent,
    FilterChangedEvent,
    DocumentLoadedEvent,
    ViewportRefreshEvent,
)
from ..filter_panel import BrushFilterMatcher, EntityFilterMatcher

from .settings_manager import SettingsManager
from .grid_renderer import GridRenderer
from .patch_tessellator import PatchTessellator
from .geometry_builder import GeometryBuilder
from .selection_handler import SelectionHandler
from .input_handler import InputHandler
from .renderer import Renderer

if TYPE_CHECKING:
    from ...core import MapDocument


class Viewport3D(QOpenGLWidget):
    """3D viewport with OpenGL rendering using ModernGL."""

    # Signal emitted when brush geometry changes (after drag ends)
    geometry_changed = pyqtSignal()

    def __init__(self, document: "MapDocument", parent=None):
        super().__init__(parent)

        self.document = document

        # Create camera
        self.camera = Camera()

        # ModernGL context
        self.ctx: moderngl.Context | None = None

        # Shader programs
        self.brush_program: moderngl.Program | None = None
        self.wireframe_program: moderngl.Program | None = None
        self.grid_program: moderngl.Program | None = None

        # Frustum culling
        self._frustum_culler = FrustumCuller()
        self._visible_brush_keys: set[tuple[int, int]] = set()
        self._culling_stats: tuple[int, int] = (0, 0)  # (visible, total)

        # Batched rendering
        self._batch_renderer: BatchedBrushRenderer | None = None

        # Spatial indexing for picking
        self._octree = BrushOctree()

        # Instanced entity marker rendering
        self._entity_renderer: InstancedMarkerRenderer | None = None

        # Visibility filters
        self._filters: dict[str, bool] = {}
        self._filtered_brushes: set[tuple[int, int]] = set()
        self._filtered_entity_ids: set[int] = set()
        self._filters_dirty = True

        # Render settings
        self.show_textures = False
        self.grid_size = 64

        # Initialize modular components (created here, used after initializeGL)
        self._settings_manager: SettingsManager | None = None
        self._grid_renderer: GridRenderer | None = None
        self._patch_tessellator: PatchTessellator | None = None
        self._geometry_builder: GeometryBuilder | None = None
        self._selection_handler: SelectionHandler | None = None
        self._input_handler: InputHandler | None = None
        self._renderer: Renderer | None = None

        # Widget settings
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)

        # Create settings manager early (before initializeGL)
        self._settings_manager = SettingsManager(self)
        self._settings_manager.load_camera_settings()
        self._settings_manager.load_colors()
        self.camera.reset()

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
        if event.source == "viewport_3d":
            return

        if self._batch_renderer is not None:
            self._batch_renderer.update_selection(event.selected_brushes)

        if self._selection_handler is not None:
            self._selection_handler.rebuild_selected_faces_vao()

        self.update()

    def _on_brush_geometry_modified_event(self, event: BrushGeometryModifiedEvent) -> None:
        """Handle brush geometry modifications from the event bus."""
        if self._geometry_builder is None:
            return

        if not event.brush_indices:
            self._geometry_builder.rebuild_geometry()
        else:
            self._geometry_builder.rebuild_specific_brushes(list(event.brush_indices))

        self.update()

    def _on_filter_changed_event(self, event: FilterChangedEvent) -> None:
        """Handle filter changes from the event bus."""
        self._filters = event.filters.copy()
        self._filters_dirty = True
        self._update_filtered_elements()
        self.update()

    def _on_document_loaded_event(self, event: DocumentLoadedEvent) -> None:
        """Handle document loaded event."""
        if self._geometry_builder is not None:
            self._geometry_builder.rebuild_geometry()
        self._filters_dirty = True
        self._update_filtered_elements()
        self.update()

    def _on_viewport_refresh_event(self, event: ViewportRefreshEvent) -> None:
        """Handle viewport refresh request."""
        if event.refresh_3d:
            if event.rebuild_geometry and self._geometry_builder is not None:
                self._geometry_builder.rebuild_geometry()
            self.update()

    def _update_filtered_elements(self):
        """Update the sets of visible brushes and entities based on filters."""
        if not self._filters_dirty:
            return

        self._filtered_brushes.clear()
        self._filtered_entity_ids.clear()

        # If no filters are set, show everything
        if not self._filters:
            for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
                self._filtered_brushes.add((entity_idx, brush_idx))
            for entity in self.document.entities:
                self._filtered_entity_ids.add(entity.index)
            self._filters_dirty = False
            return

        # Filter brushes
        for entity_idx, brush_idx, brush in self.document.iter_all_geometry():
            if BrushFilterMatcher.should_show_brush(brush, self._filters):
                self._filtered_brushes.add((entity_idx, brush_idx))

        # Filter entities (point entities only)
        for entity in self.document.entities:
            if EntityFilterMatcher.should_show_entity(entity, self._filters):
                self._filtered_entity_ids.add(entity.index)

        # Update entity renderer with filtered entities
        if self._entity_renderer is not None:
            filtered_entities = [
                e for e in self.document.entities
                if e.index in self._filtered_entity_ids
            ]
            self._entity_renderer.update_entities(filtered_entities)

        # Update batch renderer with filtered brushes
        if self._batch_renderer is not None:
            if self._filters:
                self._batch_renderer.set_filtered_brush_keys(self._filtered_brushes)
            else:
                self._batch_renderer.set_filtered_brush_keys(None)

        self._filters_dirty = False

    # =========================================================================
    # Public API
    # =========================================================================

    def reload_settings(self):
        """Reload settings (call after preferences change)."""
        if self._settings_manager is not None:
            self._settings_manager.reload()

        if self._batch_renderer is not None:
            self._batch_renderer.set_enabled(self._settings_manager.batching_enabled)

        if self._entity_renderer is not None:
            self._entity_renderer.set_enabled(self._settings_manager.entity_markers_enabled)
            self._entity_renderer.set_marker_size(self._settings_manager.entity_marker_size)

        self.update()

    def set_filters(self, filters: dict[str, bool]):
        """Set visibility filters and update rendering."""
        self._filters = filters.copy()
        self._filters_dirty = True
        self._update_filtered_elements()
        self.update()

    def set_document(self, document: "MapDocument", progress_callback=None):
        """Set the document to display."""
        self.document = document
        if self.ctx is not None and self._geometry_builder is not None:
            try:
                self.makeCurrent()
                self._geometry_builder.rebuild_geometry(progress_callback)
            except Exception as e:
                print(f"Error rebuilding geometry: {e}")
                import traceback
                traceback.print_exc()
            finally:
                try:
                    self.doneCurrent()
                except Exception:
                    pass
        self.update()

    def _rebuild_moved_brushes(self):
        """Rebuild geometry for moved brushes (called by 2D viewport after drag)."""
        if self._geometry_builder is not None:
            self._geometry_builder.rebuild_moved_brushes()

    def force_redraw(self):
        """Force an immediate redraw of the viewport."""
        if self.ctx is not None:
            self.makeCurrent()
            self.paintGL()
            self.doneCurrent()
            self.context().swapBuffers(self.context().surface())

    def get_culling_stats(self) -> tuple[int, int, bool]:
        """Get frustum culling statistics."""
        return (*self._culling_stats, self._settings_manager.culling_enabled if self._settings_manager else True)

    def set_culling_enabled(self, enabled: bool):
        """Enable or disable frustum culling."""
        if self._settings_manager is not None:
            self._settings_manager.culling_enabled = enabled
        self.update()

    def get_batching_stats(self) -> dict:
        """Get batched rendering statistics."""
        if self._batch_renderer and self._settings_manager and self._settings_manager.batching_enabled:
            return self._batch_renderer.get_stats()
        return {}

    def set_batching_enabled(self, enabled: bool):
        """Enable or disable batched rendering."""
        if self._settings_manager is not None:
            self._settings_manager.batching_enabled = enabled
        if self._batch_renderer:
            self._batch_renderer.set_enabled(enabled)
        self.update()

    def get_octree_stats(self) -> dict:
        """Get octree statistics."""
        stats = self._octree.get_stats()
        stats['enabled'] = self._settings_manager.octree_enabled if self._settings_manager else True
        return stats

    def set_octree_enabled(self, enabled: bool):
        """Enable or disable octree-accelerated picking."""
        if self._settings_manager is not None:
            self._settings_manager.octree_enabled = enabled

    # =========================================================================
    # OpenGL Lifecycle
    # =========================================================================

    def initializeGL(self):
        """Initialize OpenGL context and resources."""
        try:
            # Create ModernGL context from existing OpenGL context
            self.ctx = moderngl.create_context()
            print(f"OpenGL initialized: {self.ctx.info['GL_RENDERER']}")

            # Enable depth testing
            self.ctx.enable(moderngl.DEPTH_TEST)
            self.ctx.enable(moderngl.CULL_FACE)
            self.ctx.front_face = 'cw'

            # Load shaders
            self._load_shaders()
            print("Shaders loaded")

            # Initialize modular components that need OpenGL context
            self._grid_renderer = GridRenderer(self)
            self._patch_tessellator = PatchTessellator(self)
            self._geometry_builder = GeometryBuilder(self)
            self._selection_handler = SelectionHandler(self)
            self._input_handler = InputHandler(self)
            self._renderer = Renderer(self)

            # Initialize batch renderer
            self._batch_renderer = BatchedBrushRenderer(
                self.ctx, self.brush_program, self.wireframe_program
            )
            self._batch_renderer.set_enabled(self._settings_manager.batching_enabled)
            print("Batch renderer initialized")

            # Initialize instanced entity marker renderer
            self._entity_renderer = InstancedMarkerRenderer(self.ctx)
            self._entity_renderer.set_enabled(self._settings_manager.entity_markers_enabled)
            self._entity_renderer.set_marker_size(self._settings_manager.entity_marker_size)
            print("Entity marker renderer initialized")

            # Create default checker texture for texture preview mode
            self._geometry_builder.create_default_texture()
            print("Default texture created")

            # Create grid geometry
            self._grid_renderer.create_grid(self.grid_size)
            self._grid_renderer.create_axis_lines()
            print("Grid created")

            # Build brush geometry
            self._geometry_builder.rebuild_geometry()
            print("Geometry built")

        except Exception as e:
            print(f"OpenGL initialization error: {e}")
            import traceback
            traceback.print_exc()
            self.ctx = None

    def _load_shaders(self):
        """Load shader programs."""
        shader_dir = Path(__file__).parent.parent.parent / "render" / "shaders"

        # Brush shader
        brush_vert = (shader_dir / "brush.vert").read_text()
        brush_frag = (shader_dir / "brush.frag").read_text()
        self.brush_program = self.ctx.program(
            vertex_shader=brush_vert,
            fragment_shader=brush_frag
        )

        # Wireframe shader
        wire_vert = (shader_dir / "wireframe.vert").read_text()
        wire_frag = (shader_dir / "wireframe.frag").read_text()
        self.wireframe_program = self.ctx.program(
            vertex_shader=wire_vert,
            fragment_shader=wire_frag
        )
        print(f"Wireframe shader uniforms: {list(self.wireframe_program)}")

        # Grid shader
        grid_vert = (shader_dir / "grid.vert").read_text()
        grid_frag = (shader_dir / "grid.frag").read_text()
        self.grid_program = self.ctx.program(
            vertex_shader=grid_vert,
            fragment_shader=grid_frag
        )

    def resizeGL(self, width: int, height: int):
        """Handle resize."""
        if self.ctx:
            self.ctx.viewport = (0, 0, width, height)
        self.camera.set_aspect(width, height)

    def paintGL(self):
        """Render the scene."""
        if self._renderer is not None:
            self._renderer.paint()

    # =========================================================================
    # Input Event Handlers
    # =========================================================================

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press."""
        if self._input_handler is not None:
            self._input_handler.handle_mouse_press(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if self._input_handler is not None:
            self._input_handler.handle_mouse_release(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move."""
        if self._input_handler is not None:
            self._input_handler.handle_mouse_move(event)

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel."""
        if self._input_handler is not None:
            self._input_handler.handle_wheel(event)

    def keyPressEvent(self, event: QKeyEvent):
        """Handle key press."""
        if self._input_handler is not None:
            self._input_handler.handle_key_press(event)

    def keyReleaseEvent(self, event: QKeyEvent):
        """Handle key release."""
        if self._input_handler is not None:
            self._input_handler.handle_key_release(event)

    def focusOutEvent(self, event):
        """Handle focus lost."""
        if self._input_handler is not None:
            self._input_handler.handle_focus_out(event)
        super().focusOutEvent(event)
