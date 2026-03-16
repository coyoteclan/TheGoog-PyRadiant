"""Main rendering orchestration for 3D viewport."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import moderngl

from ...render.instanced_renderer import MarkerShape

if TYPE_CHECKING:
    from .viewport_3d_gl import Viewport3D


class Renderer:
    """Orchestrates all 3D viewport rendering."""

    def __init__(self, viewport: "Viewport3D"):
        self.viewport = viewport

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    def _get_brush_by_key(self, brush_key: tuple[int, int]):
        """Get a brush by its (entity_idx, brush_idx) key."""
        entity_idx, brush_idx = brush_key
        return self.viewport.document.get_brush(entity_idx, brush_idx)

    def paint(self):
        """Main rendering method - renders the complete scene."""
        if self.ctx is None:
            return

        try:
            # Use Qt's framebuffer (critical for Windows/PyQt6)
            fbo = self.ctx.detect_framebuffer()
            fbo.use()

            settings = self.viewport._settings_manager

            # Clear with background color from settings
            bg = settings.bg_color
            self.ctx.clear(bg[0], bg[1], bg[2], bg[3] if len(bg) > 3 else 1.0)

            # Get matrices (transpose for OpenGL column-major order)
            mvp_raw = self.viewport.camera.get_view_projection_matrix()
            mvp = mvp_raw.T.copy()
            model = np.eye(4, dtype='f4')

            # Update frustum culling
            if settings.culling_enabled:
                self.viewport._frustum_culler.update_frustum(mvp_raw)
                self.viewport._visible_brush_keys = self.viewport._frustum_culler.get_visible_brush_keys()
                self.viewport._culling_stats = self.viewport._frustum_culler.get_culling_stats()

            # Draw grid and axes
            self.viewport._grid_renderer.render_grid(mvp)
            self.viewport._grid_renderer.render_axes(mvp)

            # Apply shader settings for solid rendering
            if settings.face_culling:
                self.ctx.enable(moderngl.CULL_FACE)
            else:
                self.ctx.disable(moderngl.CULL_FACE)

            if settings.solid_depth_test:
                self.ctx.enable(moderngl.DEPTH_TEST)
            else:
                self.ctx.disable(moderngl.DEPTH_TEST)

            # Enable alpha blending for transparent textures
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)

            vao_color = settings.vao_color
            selection_color = settings.selection_color
            outline_color = settings.brush_outline_color
            wireframe_depth_test = settings.wireframe_depth_test
            backface_culling_3d = settings.backface_culling_3d

            # Use batched rendering if enabled
            use_batched = settings.batching_enabled and self.viewport._batch_renderer is not None

            if use_batched:
                self._render_batched(mvp, model, vao_color, selection_color, outline_color,
                                    wireframe_depth_test, backface_culling_3d)
            else:
                self._render_individual(mvp, model, vao_color, selection_color, outline_color,
                                       wireframe_depth_test, backface_culling_3d)

            # Render patches (terrain and curves) - not batched
            self._render_patches(mvp, model, vao_color, selection_color, outline_color,
                               wireframe_depth_test, backface_culling_3d)

            # Draw selected faces highlight
            self._render_selected_faces(mvp, model, vao_color)

            # Draw entity markers using instanced rendering
            self._render_entity_markers()

            # Disable blending after rendering (restore state)
            self.ctx.disable(moderngl.BLEND)

        except Exception as e:
            print(f"Render error: {e}")
            import traceback
            traceback.print_exc()

    def _render_batched(self, mvp: np.ndarray, model: np.ndarray,
                        vao_color: tuple, selection_color: tuple, outline_color: tuple,
                        wireframe_depth_test: bool, backface_culling_3d: bool):
        """Render brushes using batched renderer."""
        settings = self.viewport._settings_manager
        batch_renderer = self.viewport._batch_renderer

        # Update batch renderer with current selection
        selected_brushes = self.viewport.document.selection.selected_brushes
        batch_renderer.update_selection(selected_brushes)

        # Set default texture for fallback (checker pattern)
        if self.viewport._geometry_builder.default_texture is not None:
            batch_renderer.set_default_texture(self.viewport._geometry_builder.default_texture)

        # Render solid brushes with per-face textures when texture mode is enabled
        batch_renderer.render_solid(
            mvp, model,
            base_color=vao_color[:3],
            selection_color=vao_color[:3],
            use_textures=self.viewport.show_textures,
            texture=self.viewport._geometry_builder.default_texture,
            use_per_face_textures=self.viewport.show_textures,
        )

        # Render wireframe overlay
        if settings.wireframe_overlay and self.viewport.wireframe_program:
            if wireframe_depth_test:
                self.ctx.enable(moderngl.DEPTH_TEST)
            else:
                self.ctx.disable(moderngl.DEPTH_TEST)

            # Set wireframe line thickness
            self.ctx.line_width = settings.wireframe_thickness

            cam_pos = self.viewport.camera.position
            batch_renderer.render_wireframe(
                mvp,
                camera_pos=(float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2])),
                outline_color=(outline_color[0], outline_color[1], outline_color[2], 0.5),
                selection_color=selection_color[:4],
                backface_culling=backface_culling_3d
            )

            # Reset line width
            self.ctx.line_width = 1.0

    def _render_individual(self, mvp: np.ndarray, model: np.ndarray,
                          vao_color: tuple, selection_color: tuple, outline_color: tuple,
                          wireframe_depth_test: bool, backface_culling_3d: bool):
        """Render brushes individually (fallback when batching disabled)."""
        settings = self.viewport._settings_manager
        geometry_builder = self.viewport._geometry_builder
        brush_program = self.viewport.brush_program
        wireframe_program = self.viewport.wireframe_program

        # Draw brushes (solid)
        if brush_program and geometry_builder.brush_vaos:
            brush_program['u_mvp'].write(mvp.tobytes())
            brush_program['u_model'].write(model.tobytes())
            brush_program['u_use_texture'].value = False
            brush_program['u_light_dir'].value = (0.5, 0.3, 1.0)

            for brush_key, vao in list(geometry_builder.brush_vaos.items()):
                # Frustum culling - skip brushes outside view
                if settings.culling_enabled and brush_key not in self.viewport._visible_brush_keys:
                    continue

                # Filter visibility - skip brushes hidden by filter
                if self.viewport._filters and brush_key not in self.viewport._filtered_brushes:
                    continue

                # Skip invalid VAOs
                if vao is None or not hasattr(vao, 'render') or hasattr(vao, 'mglo') and vao.mglo is None:
                    continue
                try:
                    is_selected = brush_key in self.viewport.document.selection.selected_brushes
                    brush_program['u_selected'].value = is_selected
                    brush_program['u_color'].value = vao_color[:3]
                    vao.render()
                except Exception:
                    pass

        # Draw wireframe overlay using cached VAOs
        if settings.wireframe_overlay and wireframe_program and geometry_builder.wireframe_vaos:
            if wireframe_depth_test:
                self.ctx.enable(moderngl.DEPTH_TEST)
            else:
                self.ctx.disable(moderngl.DEPTH_TEST)

            self.ctx.line_width = settings.wireframe_thickness

            wireframe_program['u_mvp'].write(mvp.tobytes())
            cam_pos = self.viewport.camera.position
            wireframe_program['u_camera_pos'].value = (float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2]))
            wireframe_program['u_backface_culling'].value = 1 if backface_culling_3d else 0

            for brush_key, (wire_vao, wire_vbo, vertex_count) in list(geometry_builder.wireframe_vaos.items()):
                # Frustum culling
                if settings.culling_enabled and brush_key not in self.viewport._visible_brush_keys:
                    continue

                # Filter visibility
                if self.viewport._filters and brush_key not in self.viewport._filtered_brushes:
                    continue

                try:
                    is_selected = brush_key in self.viewport.document.selection.selected_brushes

                    if is_selected:
                        wireframe_program['u_color'].value = selection_color[:4]
                    else:
                        wireframe_program['u_color'].value = (outline_color[0], outline_color[1], outline_color[2], 0.5)

                    wire_vao.render(moderngl.LINES)
                except Exception:
                    pass

            self.ctx.line_width = 1.0

    def _render_patches(self, mvp: np.ndarray, model: np.ndarray,
                       vao_color: tuple, selection_color: tuple, outline_color: tuple,
                       wireframe_depth_test: bool, backface_culling_3d: bool):
        """Render terrain patches and curves."""
        from ...core.texture_manager import get_texture_manager

        settings = self.viewport._settings_manager
        tessellator = self.viewport._patch_tessellator
        brush_program = self.viewport.brush_program
        wireframe_program = self.viewport.wireframe_program

        if not tessellator.patch_vaos and not tessellator.patch_wireframe_vaos:
            return

        # Get selected brushes for highlighting
        selected_brushes = self.viewport.document.selection.selected_brushes

        # Determine if filters are active
        has_filters = bool(self.viewport._filters)
        visible_brushes = self.viewport._filtered_brushes if has_filters else None

        # Get texture manager for patch textures
        texture_manager = get_texture_manager()
        use_textures = self.viewport.show_textures

        # Render solid patches
        if brush_program and tessellator.patch_vaos:
            brush_program['u_mvp'].write(mvp.tobytes())
            brush_program['u_model'].write(model.tobytes())
            brush_program['u_light_dir'].value = (0.5, 0.3, 1.0)

            if 'u_texture' in brush_program:
                brush_program['u_texture'].value = 0

            # Disable face culling for patches (they're often double-sided terrain)
            self.ctx.disable(moderngl.CULL_FACE)

            for patch_key, (vao, vbo, vertex_count) in tessellator.patch_vaos.items():
                # Frustum culling
                if settings.culling_enabled and patch_key not in self.viewport._visible_brush_keys:
                    continue

                # Filter visibility
                if visible_brushes is not None and patch_key not in visible_brushes:
                    continue

                try:
                    is_selected = patch_key in selected_brushes
                    brush_program['u_selected'].value = is_selected
                    brush_program['u_color'].value = vao_color[:3]

                    # Try to get texture for this patch
                    texture_bound = False
                    if use_textures:
                        # Get the brush to find its shader
                        brush = self._get_brush_by_key(patch_key)
                        if brush and brush.patch:
                            shader_name = brush.patch.shader
                            gpu_tex = texture_manager.get_gpu_texture(self.ctx, shader_name)
                            if gpu_tex is not None:
                                gpu_tex.use(location=0)
                                brush_program['u_use_texture'].value = True
                                texture_bound = True

                    if not texture_bound:
                        brush_program['u_use_texture'].value = False

                    vao.render(moderngl.TRIANGLES)
                except Exception as e:
                    print(f"Error rendering solid patch {patch_key}: {e}")

            # Re-enable face culling if it was enabled
            if settings.face_culling:
                self.ctx.enable(moderngl.CULL_FACE)

        # Render patch wireframe (grid lines)
        if settings.wireframe_overlay and wireframe_program and tessellator.patch_wireframe_vaos:
            if wireframe_depth_test:
                self.ctx.enable(moderngl.DEPTH_TEST)
            else:
                self.ctx.disable(moderngl.DEPTH_TEST)

            self.ctx.line_width = settings.wireframe_thickness

            wireframe_program['u_mvp'].write(mvp.tobytes())
            cam_pos = self.viewport.camera.position
            wireframe_program['u_camera_pos'].value = (float(cam_pos[0]), float(cam_pos[1]), float(cam_pos[2]))
            wireframe_program['u_backface_culling'].value = 0  # No backface culling for patches

            for patch_key, (wire_vao, wire_vbo, vertex_count) in tessellator.patch_wireframe_vaos.items():
                if settings.culling_enabled and patch_key not in self.viewport._visible_brush_keys:
                    continue

                if visible_brushes is not None and patch_key not in visible_brushes:
                    continue

                try:
                    is_selected = patch_key in selected_brushes
                    if is_selected:
                        wireframe_program['u_color'].value = selection_color[:4]
                    else:
                        wireframe_program['u_color'].value = (outline_color[0], outline_color[1], outline_color[2], 0.5)

                    wire_vao.render(moderngl.LINES)
                except Exception:
                    pass

        # Render patch diagonals (thinner lines)
        if settings.wireframe_overlay and wireframe_program and tessellator.patch_diagonal_vaos:
            self.ctx.line_width = 0.5  # Thinner for diagonals

            for patch_key, (diag_vao, diag_vbo, vertex_count) in tessellator.patch_diagonal_vaos.items():
                if settings.culling_enabled and patch_key not in self.viewport._visible_brush_keys:
                    continue

                if visible_brushes is not None and patch_key not in visible_brushes:
                    continue

                try:
                    is_selected = patch_key in selected_brushes
                    if is_selected:
                        # Slightly dimmer selection color for diagonals
                        wireframe_program['u_color'].value = (
                            selection_color[0] * 0.8,
                            selection_color[1] * 0.8,
                            selection_color[2] * 0.8,
                            0.6
                        )
                    else:
                        # Dimmer outline color for diagonals
                        wireframe_program['u_color'].value = (
                            outline_color[0] * 0.5,
                            outline_color[1] * 0.5,
                            outline_color[2] * 0.5,
                            0.3
                        )

                    diag_vao.render(moderngl.LINES)
                except Exception:
                    pass

            self.ctx.line_width = 1.0  # Reset

    def _render_selected_faces(self, mvp: np.ndarray, model: np.ndarray, vao_color: tuple):
        """Render selected face highlighting."""
        settings = self.viewport._settings_manager
        selection_handler = self.viewport._selection_handler
        brush_program = self.viewport.brush_program

        if selection_handler.selected_faces_vao is None or selection_handler.selected_faces_vertex_count == 0:
            return

        # Use brush program for face rendering
        brush_program['u_mvp'].write(mvp.tobytes())
        brush_program['u_model'].write(model.tobytes())
        brush_program['u_use_texture'].value = False
        brush_program['u_selected'].value = True
        brush_program['u_color'].value = vao_color[:3]
        brush_program['u_light_dir'].value = (0.5, 0.3, 1.0)

        # Disable depth test briefly to draw on top, then re-enable
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.CULL_FACE)

        selection_handler.selected_faces_vao.render()

        # Restore state
        self.ctx.enable(moderngl.DEPTH_TEST)
        if settings.face_culling:
            self.ctx.enable(moderngl.CULL_FACE)

    def _render_entity_markers(self):
        """Render entity markers using instanced rendering."""
        settings = self.viewport._settings_manager
        entity_renderer = self.viewport._entity_renderer

        if not settings.entity_markers_enabled or entity_renderer is None:
            return

        # Get camera vectors for billboarding
        view_matrix = self.viewport.camera.get_view_matrix()
        projection_matrix = self.viewport.camera.get_projection_matrix()

        # Extract camera right and up vectors from view matrix
        camera_right = np.array([view_matrix[0, 0], view_matrix[1, 0], view_matrix[2, 0]])
        camera_up = np.array([view_matrix[0, 1], view_matrix[1, 1], view_matrix[2, 1]])

        entity_renderer.render(
            view_matrix,
            projection_matrix,
            camera_right,
            camera_up,
            MarkerShape.CIRCLE
        )
