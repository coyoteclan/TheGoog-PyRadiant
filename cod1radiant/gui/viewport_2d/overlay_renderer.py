"""Overlay rendering (handles, previews, labels) for 2D viewport."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import moderngl

if TYPE_CHECKING:
    from .viewport_2d_gl import Viewport2DGL

from ..tools import EditMode, ClipSide

from ...core import Brush, get_brush_bounds


class OverlayRenderer:
    """Handles overlay rendering (handles, previews, text) for 2D viewport."""

    def __init__(self, viewport: "Viewport2DGL"):
        self.viewport = viewport
        self._quad_program: moderngl.Program | None = None

    @property
    def ctx(self) -> moderngl.Context | None:
        return self.viewport.ctx

    @property
    def line_program(self) -> moderngl.Program | None:
        return self.viewport.line_program

    def draw_tool_overlays(self):
        """Draw tool overlays using ModernGL."""
        if self.ctx is None or self.line_program is None:
            return

        v = self.viewport

        # Draw resize handles or edge handles based on mode
        if v._edit_mode == EditMode.RESIZE:
            self._draw_resize_handles_gl()
        elif v._edit_mode == EditMode.EDGE:
            self._draw_edge_handles_gl()

        # Draw brush creation preview
        if v._brush_creation_tool.is_creating():
            self._draw_brush_preview_gl()

        # Draw clipping tool overlay
        if v._clipping_tool.is_active():
            self._draw_clipping_overlay_gl()

    def _draw_resize_handles_gl(self):
        """Draw resize handles using ModernGL."""
        vp = self.viewport
        selected = vp.document.selection.selected_brushes
        if not selected:
            return

        axis_h, axis_v = vp._get_axes()

        min_h, max_h = float('inf'), float('-inf')
        min_v, max_v = float('inf'), float('-inf')

        for entity_idx, brush_idx in selected:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush is None or not brush.is_regular:
                continue
            bounds = get_brush_bounds(brush)
            if bounds:
                b_min, b_max = bounds
                b_min_arr = (b_min.x, b_min.y, b_min.z)
                b_max_arr = (b_max.x, b_max.y, b_max.z)
                min_h = min(min_h, b_min_arr[axis_h])
                max_h = max(max_h, b_max_arr[axis_h])
                min_v = min(min_v, b_min_arr[axis_v])
                max_v = max(max_v, b_max_arr[axis_v])

        if min_h == float('inf'):
            return

        # Handle positions in world coordinates
        handles = [
            (min_h, max_v),  # nw
            (max_h, max_v),  # ne
            (max_h, min_v),  # se
            (min_h, min_v),  # sw
            ((min_h + max_h) / 2, max_v),  # n
            ((min_h + max_h) / 2, min_v),  # s
            (max_h, (min_v + max_v) / 2),  # e
            (min_h, (min_v + max_v) / 2),  # w
        ]

        handle_size = 6.0 / vp.zoom

        lines = []
        for hx, hy in handles:
            hs = handle_size / 2
            lines.extend([
                hx - hs, hy - hs, hx + hs, hy - hs,
                hx + hs, hy - hs, hx + hs, hy + hs,
                hx + hs, hy + hs, hx - hs, hy + hs,
                hx - hs, hy + hs, hx - hs, hy - hs,
            ])

        if lines:
            vertices = np.array(lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )

            self.line_program['u_color'].value = vp._selection_color_tuple[:4]
            self.ctx.line_width = 2.0
            vao.render(moderngl.LINES)
            self.ctx.line_width = 1.0

            vao.release()
            vbo.release()

    def _draw_edge_handles_gl(self):
        """Draw edge handles using ModernGL."""
        vp = self.viewport
        if not vp.document.selection.selected_brushes:
            return

        handles = vp._edge_tool._get_edge_handles()
        if not handles:
            return

        handle_size = 6.0 / vp.zoom
        hs = handle_size / 2

        drawn_positions = set()
        square_lines = []
        circle_lines = []

        for handle in handles:
            pos_2d = handle.get('pos_2d')
            if not pos_2d:
                continue

            key = (round(pos_2d[0], 1), round(pos_2d[1], 1))
            if key in drawn_positions:
                continue
            drawn_positions.add(key)

            hx, hy = pos_2d[0], pos_2d[1]

            if handle.get('is_perpendicular', False):
                for i in range(8):
                    angle1 = i * math.pi / 4
                    angle2 = (i + 1) * math.pi / 4
                    x1 = hx + hs * math.cos(angle1)
                    y1 = hy + hs * math.sin(angle1)
                    x2 = hx + hs * math.cos(angle2)
                    y2 = hy + hs * math.sin(angle2)
                    circle_lines.extend([x1, y1, x2, y2])
            else:
                square_lines.extend([
                    hx - hs, hy - hs, hx + hs, hy - hs,
                    hx + hs, hy - hs, hx + hs, hy + hs,
                    hx + hs, hy + hs, hx - hs, hy + hs,
                    hx - hs, hy + hs, hx - hs, hy - hs,
                ])

        # Draw square handles (blue)
        if square_lines:
            vertices = np.array(square_lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            self.line_program['u_color'].value = (0.0, 0.5, 1.0, 1.0)
            self.ctx.line_width = 2.0
            vao.render(moderngl.LINES)
            self.ctx.line_width = 1.0
            vao.release()
            vbo.release()

        # Draw circle handles (blue)
        if circle_lines:
            vertices = np.array(circle_lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            self.line_program['u_color'].value = (0.0, 0.5, 1.0, 1.0)
            self.ctx.line_width = 2.0
            vao.render(moderngl.LINES)
            self.ctx.line_width = 1.0
            vao.release()
            vbo.release()

    def _draw_brush_preview_gl(self):
        """Draw brush creation preview rectangle using ModernGL."""
        v = self.viewport
        if not v._brush_creation_tool._creating:
            return

        start = v._brush_creation_tool._start_world
        end = v._brush_creation_tool._end_world
        if not start or not end:
            return

        x1, y1 = start
        x2, y2 = end

        lines = [
            x1, y1, x2, y1,
            x2, y1, x2, y2,
            x2, y2, x1, y2,
            x1, y2, x1, y1,
        ]

        vertices = np.array(lines, dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.line_program,
            [(vbo, '2f', 'in_position')]
        )

        self.line_program['u_color'].value = (0.0, 1.0, 0.0, 1.0)
        self.ctx.line_width = 2.0
        vao.render(moderngl.LINES)
        self.ctx.line_width = 1.0

        vao.release()
        vbo.release()

    def _draw_clipping_overlay_gl(self):
        """Draw clipping tool overlay."""
        v = self.viewport
        if not v._clipping_tool.is_active():
            return

        point1 = v._clipping_tool._point1
        point2 = v._clipping_tool._point2
        point2_confirmed = v._clipping_tool._point2_confirmed

        line_color = (1.0, 1.0, 0.0, 1.0)
        point_color = (1.0, 0.0, 0.0, 1.0)
        arrow_color = (0.0, 1.0, 0.0, 1.0)
        mode_color = (1.0, 0.5, 0.0, 1.0)

        # Draw "CLIP MODE" indicator
        if v.bitmap_font is not None:
            w, h = v.width(), v.height()
            mode_text = "*** CLIP MODE ***"
            text_w, text_h = v.bitmap_font.measure_text(mode_text)
            text_x = (w - text_w) // 2
            text_y = 10

            self._draw_filled_rect_gl(
                int(text_x - 5), int(text_y - 2),
                text_w + 10, text_h + 4,
                (0.3, 0.1, 0.0, 0.8)
            )
            v.bitmap_font.draw_text(
                mode_text, text_x, text_y,
                color=mode_color,
                screen_width=w, screen_height=h
            )

        point_radius = 6.0 / v.zoom

        lines = []
        point_lines = []

        # Draw first point if set
        if point1 is not None:
            px, py = point1
            pr = point_radius / 2
            for i in range(8):
                angle1 = i * math.pi / 4
                angle2 = (i + 1) * math.pi / 4
                x1 = px + pr * math.cos(angle1)
                y1 = py + pr * math.sin(angle1)
                x2 = px + pr * math.cos(angle2)
                y2 = py + pr * math.sin(angle2)
                point_lines.extend([x1, y1, x2, y2])

        # Draw second point and line if set
        if point1 is not None and point2 is not None:
            p1x, p1y = point1
            p2x, p2y = point2

            lines.extend([p1x, p1y, p2x, p2y])

            px, py = point2
            pr = point_radius / 2
            for i in range(8):
                angle1 = i * math.pi / 4
                angle2 = (i + 1) * math.pi / 4
                x1 = px + pr * math.cos(angle1)
                y1 = py + pr * math.sin(angle1)
                x2 = px + pr * math.cos(angle2)
                y2 = py + pr * math.sin(angle2)
                point_lines.extend([x1, y1, x2, y2])

        # Render clip line (yellow)
        if lines:
            vertices = np.array(lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            self.line_program['u_color'].value = line_color
            self.ctx.line_width = 2.0
            vao.render(moderngl.LINES)
            self.ctx.line_width = 1.0
            vao.release()
            vbo.release()

        # Render clip points (red)
        if point_lines:
            vertices = np.array(point_lines, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )
            self.line_program['u_color'].value = point_color
            self.ctx.line_width = 2.0
            vao.render(moderngl.LINES)
            self.ctx.line_width = 1.0
            vao.release()
            vbo.release()

        # Draw direction arrow
        if point1 is not None and point2 is not None:
            self._draw_clip_direction_arrow(point1, point2, arrow_color)

        # Draw clipped brush preview
        if point1 is not None and point2 is not None and point2_confirmed:
            self._draw_clipped_brush_preview(point1, point2)

    def _draw_clip_direction_arrow(self, point1: tuple, point2: tuple, arrow_color: tuple):
        """Draw direction arrow showing which side is kept."""
        v = self.viewport
        clip_side = v._clipping_tool._clip_side

        if clip_side == ClipSide.BOTH:
            return

        p1x, p1y = point1
        p2x, p2y = point2

        dx = p2x - p1x
        dy = p2y - p1y
        length = np.sqrt(dx * dx + dy * dy)
        if length <= 0.001:
            return

        perp_x = -dy / length
        perp_y = dx / length

        if clip_side == ClipSide.BACK:
            perp_x = -perp_x
            perp_y = -perp_y

        mid_x = (p1x + p2x) / 2
        mid_y = (p1y + p2y) / 2

        arrow_len = 30.0 / v.zoom

        end_x = mid_x + perp_x * arrow_len
        end_y = mid_y + perp_y * arrow_len

        arrow_lines = [mid_x, mid_y, end_x, end_y]

        head_size = 8.0 / v.zoom
        angle = math.atan2(perp_y, perp_x)
        head1_x = end_x - head_size * math.cos(angle - 0.5)
        head1_y = end_y - head_size * math.sin(angle - 0.5)
        head2_x = end_x - head_size * math.cos(angle + 0.5)
        head2_y = end_y - head_size * math.sin(angle + 0.5)

        arrow_lines.extend([end_x, end_y, head1_x, head1_y])
        arrow_lines.extend([end_x, end_y, head2_x, head2_y])

        vertices = np.array(arrow_lines, dtype='f4')
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.line_program,
            [(vbo, '2f', 'in_position')]
        )
        self.line_program['u_color'].value = arrow_color
        self.ctx.line_width = 2.0
        vao.render(moderngl.LINES)
        self.ctx.line_width = 1.0
        vao.release()
        vbo.release()

    def _draw_clipped_brush_preview(self, point1: tuple, point2: tuple):
        """Draw semi-transparent preview of clipped brush result."""
        vp = self.viewport
        clip_side = vp._clipping_tool._clip_side
        axis_h, axis_v = vp._get_axes()

        selected = vp.document.selection.selected_brushes
        if not selected:
            return

        dx = point2[0] - point1[0]
        dy = point2[1] - point1[1]
        length = np.sqrt(dx * dx + dy * dy)
        if length < 0.001:
            return

        normal_x = -dy / length
        normal_y = dx / length

        if clip_side == ClipSide.BACK:
            normal_x = -normal_x
            normal_y = -normal_y

        d = normal_x * point1[0] + normal_y * point1[1]

        all_triangles = []

        for entity_idx, brush_idx in selected:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush is None or not brush.is_regular:
                continue

            bounds = get_brush_bounds(brush)
            if not bounds:
                continue
            b_min, b_max = bounds
            b_min_arr = (b_min.x, b_min.y, b_min.z)
            b_max_arr = (b_max.x, b_max.y, b_max.z)
            min_h, max_h = b_min_arr[axis_h], b_max_arr[axis_h]
            min_v, max_v = b_min_arr[axis_v], b_max_arr[axis_v]

            rect_verts = [
                (min_h, min_v),
                (max_h, min_v),
                (max_h, max_v),
                (min_h, max_v),
            ]

            clipped_verts = []

            for i in range(4):
                v1 = rect_verts[i]
                v2 = rect_verts[(i + 1) % 4]

                dist1 = normal_x * v1[0] + normal_y * v1[1] - d
                dist2 = normal_x * v2[0] + normal_y * v2[1] - d

                if dist1 >= 0:
                    clipped_verts.append(v1)

                if (dist1 >= 0) != (dist2 >= 0):
                    t = dist1 / (dist1 - dist2)
                    ix = v1[0] + t * (v2[0] - v1[0])
                    iy = v1[1] + t * (v2[1] - v1[1])
                    clipped_verts.append((ix, iy))

            if len(clipped_verts) >= 3:
                for i in range(1, len(clipped_verts) - 1):
                    all_triangles.extend([
                        clipped_verts[0][0], clipped_verts[0][1],
                        clipped_verts[i][0], clipped_verts[i][1],
                        clipped_verts[i + 1][0], clipped_verts[i + 1][1],
                    ])

        if all_triangles:
            vertices = np.array(all_triangles, dtype='f4')
            vbo = self.ctx.buffer(vertices.tobytes())
            vao = self.ctx.vertex_array(
                self.line_program,
                [(vbo, '2f', 'in_position')]
            )

            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
            self.line_program['u_color'].value = (0.0, 0.8, 0.0, 0.25)
            vao.render(moderngl.TRIANGLES)
            self.ctx.disable(moderngl.BLEND)

            vao.release()
            vbo.release()

    def draw_text_overlays(self):
        """Draw all text labels using BitmapFont."""
        v = self.viewport
        if v.bitmap_font is None:
            return

        w, h = v.width(), v.height()

        # Draw axis labels in top-left corner
        if v._show_axis_labels:
            self._draw_axis_labels_gl(w, h)

        # Draw brush creation dimensions
        if v._brush_creation_tool.is_creating():
            self._draw_brush_dimensions_gl(w, h)
        elif v.document.selection.selected_brushes:
            self._draw_selection_info_gl(w, h)

    def _draw_axis_labels_gl(self, screen_width: int, screen_height: int):
        """Draw axis labels using BitmapFont."""
        v = self.viewport
        if v.bitmap_font is None:
            return

        h_label, v_label = v._get_axis_labels()
        view_name = v._get_view_name()

        self._draw_filled_rect_gl(5, 5, 75, 55, (0.0, 0.0, 0.0, 0.6))

        v.bitmap_font.draw_text(
            view_name, 10, 8,
            color=(0.8, 0.8, 0.8, 1.0),
            screen_width=screen_width, screen_height=screen_height
        )

        h_color = self._get_axis_color_gl(h_label)
        v.bitmap_font.draw_text(
            f"{h_label} →", 10, 25,
            color=h_color,
            screen_width=screen_width, screen_height=screen_height
        )

        v_color = self._get_axis_color_gl(v_label)
        v.bitmap_font.draw_text(
            f"{v_label} ↑", 10, 40,
            color=v_color,
            screen_width=screen_width, screen_height=screen_height
        )

    def _draw_brush_dimensions_gl(self, screen_width: int, screen_height: int):
        """Draw dimension labels during brush creation."""
        v = self.viewport
        if v.bitmap_font is None:
            return

        start = v._brush_creation_tool._start_world
        end = v._brush_creation_tool._end_world
        if not start or not end:
            return

        x1, y1 = start
        x2, y2 = end

        width = abs(x2 - x1)
        height = abs(y2 - y1)

        h_label, v_label = v._get_axis_labels()

        p_tl = v.world_to_screen(min(x1, x2), max(y1, y2))
        p_tr = v.world_to_screen(max(x1, x2), max(y1, y2))
        p_br = v.world_to_screen(max(x1, x2), min(y1, y2))

        label_color = (1.0, 0.4, 0.4, 1.0)

        # Width label
        width_text = f"{h_label}: {width:.0f}"
        text_w, text_h = v.bitmap_font.measure_text(width_text)
        text_x = (p_tl.x() + p_tr.x()) / 2 - text_w / 2
        text_y = p_tl.y() - text_h - 5

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        v.bitmap_font.draw_text(
            width_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Height label
        height_text = f"{v_label}: {height:.0f}"
        text_w, text_h = v.bitmap_font.measure_text(height_text)
        text_x = p_tr.x() + 5
        text_y = (p_tr.y() + p_br.y()) / 2 - text_h / 2

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        v.bitmap_font.draw_text(
            height_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Corner coordinate
        coord_text = f"({min(x1, x2):.0f}, {max(y1, y2):.0f})"
        text_w, text_h = v.bitmap_font.measure_text(coord_text)
        text_x = p_tl.x()
        text_y = p_tl.y() - text_h * 2 - 10

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        v.bitmap_font.draw_text(
            coord_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

    def _draw_selection_info_gl(self, screen_width: int, screen_height: int):
        """Draw bounding box info for selected brushes."""
        vp = self.viewport
        if vp.bitmap_font is None:
            return

        selected = vp.document.selection.selected_brushes
        if not selected:
            return

        axis_h, axis_v = vp._get_axes()
        h_label, v_label = vp._get_axis_labels()

        min_h, max_h = float('inf'), float('-inf')
        min_v, max_v = float('inf'), float('-inf')

        for entity_idx, brush_idx in selected:
            brush = vp.document.get_brush(entity_idx, brush_idx)
            if brush is None or not brush.is_regular:
                continue
            bounds = get_brush_bounds(brush)
            if bounds:
                b_min, b_max = bounds
                b_min_arr = (b_min.x, b_min.y, b_min.z)
                b_max_arr = (b_max.x, b_max.y, b_max.z)
                min_h = min(min_h, b_min_arr[axis_h])
                max_h = max(max_h, b_max_arr[axis_h])
                min_v = min(min_v, b_min_arr[axis_v])
                max_v = max(max_v, b_max_arr[axis_v])

        if min_h == float('inf'):
            return

        width = max_h - min_h
        height = max_v - min_v

        p_tl = vp.world_to_screen(min_h, max_v)
        p_tr = vp.world_to_screen(max_h, max_v)
        p_br = vp.world_to_screen(max_h, min_v)

        label_color = (0.4, 0.8, 1.0, 1.0)

        # Width label
        width_text = f"{h_label}: {width:.0f}"
        text_w, text_h = vp.bitmap_font.measure_text(width_text)
        text_x = (p_tl.x() + p_tr.x()) / 2 - text_w / 2
        text_y = p_tl.y() - text_h - 5

        text_x = max(5, min(text_x, screen_width - text_w - 5))
        text_y = max(60, text_y)

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        vp.bitmap_font.draw_text(
            width_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Height label
        height_text = f"{v_label}: {height:.0f}"
        text_w, text_h = vp.bitmap_font.measure_text(height_text)
        text_x = p_tr.x() + 5
        text_y = (p_tr.y() + p_br.y()) / 2 - text_h / 2

        text_x = min(text_x, screen_width - text_w - 5)
        text_y = max(60, min(text_y, screen_height - text_h - 5))

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        vp.bitmap_font.draw_text(
            height_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Top-left corner
        tl_text = f"({min_h:.0f}, {max_v:.0f})"
        text_w, text_h = vp.bitmap_font.measure_text(tl_text)
        text_x = p_tl.x()
        text_y = p_tl.y() - text_h * 2 - 10

        text_x = max(5, min(text_x, screen_width - text_w - 5))
        text_y = max(60, text_y)

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        vp.bitmap_font.draw_text(
            tl_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Bottom-right corner
        br_text = f"({max_h:.0f}, {min_v:.0f})"
        text_w, text_h = vp.bitmap_font.measure_text(br_text)
        text_x = p_br.x() + 5
        text_y = p_br.y() + 5

        text_x = min(text_x, screen_width - text_w - 5)
        text_y = min(text_y, screen_height - text_h - 5)

        self._draw_filled_rect_gl(
            int(text_x - 3), int(text_y - 2),
            text_w + 6, text_h + 4,
            (0.0, 0.0, 0.0, 0.7)
        )
        vp.bitmap_font.draw_text(
            br_text, text_x, text_y,
            color=label_color,
            screen_width=screen_width, screen_height=screen_height
        )

        # Selection count
        if len(selected) > 1:
            count_text = f"{len(selected)} brushes"
            text_w, text_h = vp.bitmap_font.measure_text(count_text)
            text_x = 10
            text_y = 60

            self._draw_filled_rect_gl(
                int(text_x - 3), int(text_y - 2),
                text_w + 6, text_h + 4,
                (0.0, 0.0, 0.0, 0.7)
            )
            vp.bitmap_font.draw_text(
                count_text, text_x, text_y,
                color=(1.0, 0.8, 0.2, 1.0),
                screen_width=screen_width, screen_height=screen_height
            )

    def _draw_filled_rect_gl(self, x: float, y: float, w: float, h: float, color: tuple):
        """Draw a filled rectangle using ModernGL."""
        if self.ctx is None:
            return

        v = self.viewport

        if self._quad_program is None:
            vert_src = """
#version 330 core
layout(location = 0) in vec2 in_position;
uniform vec2 u_screen_size;

void main() {
    vec2 ndc = (in_position / u_screen_size) * 2.0 - 1.0;
    ndc.y = -ndc.y;
    gl_Position = vec4(ndc, 0.0, 1.0);
}
"""
            frag_src = """
#version 330 core
out vec4 fragColor;
uniform vec4 u_color;

void main() {
    fragColor = u_color;
}
"""
            try:
                self._quad_program = self.ctx.program(
                    vertex_shader=vert_src,
                    fragment_shader=frag_src
                )
            except Exception as e:
                print(f"Failed to create quad shader: {e}")
                return

        x0, y0 = x, y
        x1, y1 = x + w, y + h

        vertices = np.array([
            x0, y0,
            x1, y0,
            x1, y1,
            x0, y0,
            x1, y1,
            x0, y1,
        ], dtype='f4')

        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self._quad_program,
            [(vbo, '2f', 'in_position')]
        )

        self._quad_program['u_screen_size'].value = (float(v.width()), float(v.height()))
        self._quad_program['u_color'].value = color

        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        vao.render(moderngl.TRIANGLES)
        self.ctx.disable(moderngl.BLEND)

        vao.release()
        vbo.release()

    def _get_axis_color_gl(self, axis_name: str) -> tuple:
        """Get the color tuple for an axis label."""
        if axis_name == 'X':
            return (0.7, 0.24, 0.24, 1.0)
        elif axis_name == 'Y':
            return (0.24, 0.7, 0.24, 1.0)
        else:  # Z
            return (0.24, 0.24, 0.7, 1.0)
