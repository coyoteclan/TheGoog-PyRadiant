"""Text rendering for ModernGL using Pillow for texture generation."""

from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import Path
import numpy as np

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

if TYPE_CHECKING:
    import moderngl


class TextRenderer:
    """Renders text as textures using Pillow and ModernGL."""

    def __init__(self, ctx: "moderngl.Context"):
        self.ctx = ctx
        self.program: "moderngl.Program" | None = None
        self._font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}
        self._texture_cache: dict[str, tuple["moderngl.Texture", int, int]] = {}

        if not HAS_PIL:
            print("Warning: Pillow not installed, text rendering disabled")
            return

        self._load_shader()

    def _load_shader(self):
        """Load the text shader program."""
        shader_dir = Path(__file__).parent / "shaders"

        vert_path = shader_dir / "text_2d.vert"
        frag_path = shader_dir / "text_2d.frag"

        if not vert_path.exists() or not frag_path.exists():
            print(f"Warning: Text shaders not found at {shader_dir}")
            return

        try:
            vert_src = vert_path.read_text()
            frag_src = frag_path.read_text()

            self.program = self.ctx.program(
                vertex_shader=vert_src,
                fragment_shader=frag_src
            )
        except Exception as e:
            print(f"Failed to load text shader: {e}")

    def get_font(self, font_name: str = "arial", size: int = 12) -> ImageFont.FreeTypeFont:
        """Get or create a font object."""
        key = (font_name.lower(), size)
        if key in self._font_cache:
            return self._font_cache[key]

        try:
            # Try to load system font
            font = ImageFont.truetype(font_name, size)
        except OSError:
            try:
                # Try common font paths
                font = ImageFont.truetype(f"{font_name}.ttf", size)
            except OSError:
                # Fall back to default
                font = ImageFont.load_default()

        self._font_cache[key] = font
        return font

    def create_text_texture(
        self,
        text: str,
        font_name: str = "arial",
        font_size: int = 14,
        color: tuple[int, int, int, int] = (255, 255, 255, 255),
        padding: int = 2
    ) -> tuple["moderngl.Texture", int, int] | None:
        """Create a texture containing rendered text.

        Returns (texture, width, height) or None if failed.
        """
        if not HAS_PIL:
            return None

        # Check cache
        cache_key = f"{text}|{font_name}|{font_size}|{color}"
        if cache_key in self._texture_cache:
            return self._texture_cache[cache_key]

        font = self.get_font(font_name, font_size)

        # Calculate text size
        # Create a temporary image to measure text
        temp_img = Image.new('RGBA', (1, 1))
        temp_draw = ImageDraw.Draw(temp_img)
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]

        # Create image with padding
        img_width = text_width + padding * 2
        img_height = text_height + padding * 2

        # Create transparent image
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Draw text
        draw.text((padding - bbox[0], padding - bbox[1]), text, font=font, fill=color)

        # Convert to bytes (flip vertically for OpenGL)
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img_data = img.tobytes()

        # Create ModernGL texture
        texture = self.ctx.texture((img_width, img_height), 4, img_data)
        texture.filter = (self.ctx.LINEAR, self.ctx.LINEAR)

        # Cache it
        self._texture_cache[cache_key] = (texture, img_width, img_height)

        return (texture, img_width, img_height)

    def draw_text_screen(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        font_name: str = "arial",
        font_size: int = 14,
        projection: np.ndarray = None
    ):
        """Draw text at screen coordinates (pixels from top-left).

        Args:
            text: Text to render
            x, y: Screen position in pixels (top-left origin)
            color: RGBA color (0-1 range)
            font_name: Font to use
            font_size: Font size in points
            projection: Orthographic projection matrix
        """
        if not HAS_PIL or self.program is None:
            return

        result = self.create_text_texture(text, font_name, font_size)
        if result is None:
            return

        texture, tex_width, tex_height = result

        # Create quad vertices (screen space)
        # Note: y is flipped for screen coords (0 at top)
        x1, y1 = x, y
        x2, y2 = x + tex_width, y + tex_height

        vertices = np.array([
            # Position    # TexCoord
            x1, y1,       0.0, 1.0,
            x2, y1,       1.0, 1.0,
            x2, y2,       1.0, 0.0,
            x1, y1,       0.0, 1.0,
            x2, y2,       1.0, 0.0,
            x1, y2,       0.0, 0.0,
        ], dtype='f4')

        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')]
        )

        # Set uniforms
        if projection is not None:
            self.program['u_projection'].write(projection.tobytes())
        self.program['u_screen_space'].value = True
        self.program['u_color'].value = color
        self.program['u_use_texture'].value = True
        self.program['u_offset'].value = (0.0, 0.0)
        self.program['u_zoom'].value = 1.0

        # Bind texture
        texture.use(0)
        self.program['u_texture'].value = 0

        # Draw
        vao.render()

        # Cleanup
        vao.release()
        vbo.release()

    def draw_text_world(
        self,
        text: str,
        x: float,
        y: float,
        color: tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0),
        font_name: str = "arial",
        font_size: int = 14,
        projection: np.ndarray = None,
        offset: tuple[float, float] = (0.0, 0.0),
        zoom: float = 1.0,
        scale: float = 1.0
    ):
        """Draw text at world coordinates.

        Args:
            text: Text to render
            x, y: World position
            color: RGBA color (0-1 range)
            font_name: Font to use
            font_size: Font size in points
            projection: Orthographic projection matrix
            offset: View offset (pan)
            zoom: View zoom level
            scale: Additional scale factor for text size in world units
        """
        if not HAS_PIL or self.program is None:
            return

        result = self.create_text_texture(text, font_name, font_size)
        if result is None:
            return

        texture, tex_width, tex_height = result

        # Scale text size to world units
        w = tex_width * scale / zoom
        h = tex_height * scale / zoom

        # Create quad vertices (world space)
        x1, y1 = x, y
        x2, y2 = x + w, y + h

        vertices = np.array([
            # Position    # TexCoord
            x1, y1,       0.0, 0.0,
            x2, y1,       1.0, 0.0,
            x2, y2,       1.0, 1.0,
            x1, y1,       0.0, 0.0,
            x2, y2,       1.0, 1.0,
            x1, y2,       0.0, 1.0,
        ], dtype='f4')

        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.vertex_array(
            self.program,
            [(vbo, '2f 2f', 'in_position', 'in_texcoord')]
        )

        # Set uniforms
        if projection is not None:
            self.program['u_projection'].write(projection.tobytes())
        self.program['u_screen_space'].value = False
        self.program['u_color'].value = color
        self.program['u_use_texture'].value = True
        self.program['u_offset'].value = offset
        self.program['u_zoom'].value = zoom

        # Bind texture
        texture.use(0)
        self.program['u_texture'].value = 0

        # Draw
        vao.render()

        # Cleanup
        vao.release()
        vbo.release()

    def clear_cache(self):
        """Clear the texture cache to free GPU memory."""
        for texture, _, _ in self._texture_cache.values():
            texture.release()
        self._texture_cache.clear()

    def release(self):
        """Release all resources."""
        self.clear_cache()
        if self.program:
            self.program.release()
            self.program = None
