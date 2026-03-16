"""Bitmap font rendering for ModernGL using a pre-generated font atlas."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
import numpy as np
import moderngl

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if TYPE_CHECKING:
    pass


class BitmapFont:
    """Bitmap font renderer using a texture atlas.

    Creates a texture atlas containing all ASCII characters at initialization,
    then renders text by drawing textured quads. This is fast and doesn't
    interfere with ModernGL state.
    """

    # Characters to include in the atlas
    CHARS = " !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~°←→↑↓"

    def __init__(self, ctx: "moderngl.Context", font_name: str = "arial", font_size: int = 14):
        self.ctx = ctx
        self.font_size = font_size
        self.program: "moderngl.Program" | None = None
        self.texture: "moderngl.Texture" | None = None

        # Character metrics: dict[char, (x, y, width, height, advance)]
        self.char_metrics: dict[str, tuple[int, int, int, int, int]] = {}
        self.atlas_width = 0
        self.atlas_height = 0
        self.line_height = 0

        if not HAS_PIL:
            print("Warning: Pillow not installed, text rendering disabled")
            return

        self._load_shader()
        self._create_atlas(font_name, font_size)

    def _load_shader(self):
        """Load the text shader program."""
        shader_dir = Path(__file__).parent / "shaders"

        vert_src = """
#version 330 core

layout(location = 0) in vec2 in_position;
layout(location = 1) in vec2 in_texcoord;

out vec2 v_texcoord;

uniform vec2 u_screen_size;

void main() {
    // Convert pixel coordinates to NDC (-1 to 1)
    vec2 ndc = (in_position / u_screen_size) * 2.0 - 1.0;
    ndc.y = -ndc.y;  // Flip Y for screen coordinates (0 at top)
    gl_Position = vec4(ndc, 0.0, 1.0);
    v_texcoord = in_texcoord;
}
"""

        frag_src = """
#version 330 core

in vec2 v_texcoord;
out vec4 fragColor;

uniform sampler2D u_texture;
uniform vec4 u_color;

void main() {
    float alpha = texture(u_texture, v_texcoord).r;
    fragColor = vec4(u_color.rgb, u_color.a * alpha);
}
"""

        try:
            self.program = self.ctx.program(
                vertex_shader=vert_src,
                fragment_shader=frag_src
            )
        except Exception as e:
            print(f"Failed to create bitmap font shader: {e}")

    def _create_atlas(self, font_name: str, font_size: int):
        """Create the font texture atlas."""
        try:
            font = ImageFont.truetype(font_name, font_size)
        except OSError:
            try:
                font = ImageFont.truetype(f"{font_name}.ttf", font_size)
            except OSError:
                font = ImageFont.load_default()

        # Calculate atlas size needed
        padding = 2
        chars_per_row = 16

        # Measure all characters
        temp_img = Image.new('L', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)

        max_width = 0
        max_height = 0

        for char in self.CHARS:
            bbox = temp_draw.textbbox((0, 0), char, font=font)
            w = bbox[2] - bbox[0] + padding * 2
            h = bbox[3] - bbox[1] + padding * 2
            max_width = max(max_width, w)
            max_height = max(max_height, h)

        # Calculate atlas dimensions
        cell_width = max_width
        cell_height = max_height
        rows = (len(self.CHARS) + chars_per_row - 1) // chars_per_row

        self.atlas_width = cell_width * chars_per_row
        self.atlas_height = cell_height * rows
        self.line_height = cell_height

        # Create atlas image
        atlas = Image.new('L', (self.atlas_width, self.atlas_height), 0)
        draw = ImageDraw.Draw(atlas)

        # Draw each character
        for i, char in enumerate(self.CHARS):
            row = i // chars_per_row
            col = i % chars_per_row

            x = col * cell_width + padding
            y = row * cell_height + padding

            # Get character bounds
            bbox = draw.textbbox((0, 0), char, font=font)
            char_width = bbox[2] - bbox[0]
            char_height = bbox[3] - bbox[1]

            # Draw character
            draw.text((x - bbox[0], y - bbox[1]), char, font=font, fill=255)

            # Store metrics (atlas position and size)
            self.char_metrics[char] = (
                col * cell_width,  # x in atlas
                row * cell_height,  # y in atlas
                cell_width,  # width in atlas
                cell_height,  # height in atlas
                char_width + padding  # advance width
            )

        # Create OpenGL texture
        atlas_data = atlas.tobytes()
        self.texture = self.ctx.texture(
            (self.atlas_width, self.atlas_height),
            1,  # Single channel (grayscale)
            atlas_data
        )
        self.texture.filter = (self.ctx.LINEAR, self.ctx.LINEAR)

    def measure_text(self, text: str) -> tuple[int, int]:
        """Measure the size of text in pixels."""
        if not self.char_metrics:
            return (0, 0)

        width = 0
        for char in text:
            if char in self.char_metrics:
                width += self.char_metrics[char][4]  # advance
            else:
                width += self.char_metrics.get(' ', (0, 0, 0, 0, 8))[4]

        return (width, self.line_height)

    def draw_text(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        screen_width: int = 800,
        screen_height: int = 600
    ):
        """Draw text at screen coordinates (pixels, origin at top-left).

        Args:
            text: Text to render
            x, y: Screen position in pixels
            color: RGBA color (0-1 range)
            screen_width, screen_height: Viewport dimensions
        """
        if not self.program or not self.texture or not self.char_metrics:
            return

        vertices = []

        cursor_x = x
        cursor_y = y

        for char in text:
            if char not in self.char_metrics:
                char = ' '

            atlas_x, atlas_y, cell_w, cell_h, advance = self.char_metrics[char]

            # Quad corners in screen pixels
            x0, y0 = cursor_x, cursor_y
            x1, y1 = cursor_x + cell_w, cursor_y + cell_h

            # Texture coordinates (0-1)
            u0 = atlas_x / self.atlas_width
            v0 = atlas_y / self.atlas_height
            u1 = (atlas_x + cell_w) / self.atlas_width
            v1 = (atlas_y + cell_h) / self.atlas_height

            # Two triangles for the quad
            vertices.extend([
                x0, y0, u0, v0,
                x1, y0, u1, v0,
                x1, y1, u1, v1,
                x0, y0, u0, v0,
                x1, y1, u1, v1,
                x0, y1, u0, v1,
            ])

            cursor_x += advance

        if not vertices:
            return

        # Create VAO/VBO
        vertices_array = np.array(vertices, dtype='f4')
        vbo = self.ctx.buffer(vertices_array.tobytes())
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')]
        )

        # Set uniforms
        self.program['u_screen_size'].value = (float(screen_width), float(screen_height))
        self.program['u_color'].value = color

        # Bind texture
        self.texture.use(0)
        self.program['u_texture'].value = 0

        # Enable blending for text rendering (alpha from texture)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

        # Draw
        vao.render()

        # Disable blending after rendering
        self.ctx.disable(moderngl.BLEND)

        # Cleanup
        vao.release()
        vbo.release()

    def draw_text_with_background(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        bg_color: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.7),
        padding: int = 3,
        screen_width: int = 800,
        screen_height: int = 600,
        line_program: "moderngl.Program" = None
    ):
        """Draw text with a background rectangle.

        Args:
            text: Text to render
            x, y: Screen position in pixels
            color: Text RGBA color (0-1 range)
            bg_color: Background RGBA color (0-1 range)
            padding: Padding around text
            screen_width, screen_height: Viewport dimensions
            line_program: Optional line program to draw background
        """
        # Measure text
        text_w, text_h = self.measure_text(text)

        # Draw background if line_program provided
        if line_program and bg_color[3] > 0:
            # Create background quad
            bx0 = x - padding
            by0 = y - padding
            bx1 = x + text_w + padding
            by1 = y + text_h + padding

            # We'd need a filled quad shader for this
            # For now, skip background or use a simple approach
            pass

        # Draw text
        self.draw_text(text, x, y, color, screen_width, screen_height)

    def release(self):
        """Release all resources."""
        if self.texture:
            self.texture.release()
            self.texture = None
        if self.program:
            self.program.release()
            self.program = None
