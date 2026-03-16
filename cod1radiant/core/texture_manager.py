"""
Texture Manager - Backend for loading and caching textures.

Provides:
- Scanning texture directories for TGA, DDS, JPG, PNG files
- Thumbnail caching (QPixmap for GUI)
- GPU texture caching (moderngl.Texture for 3D rendering)
- Search and filter functionality

This is a singleton class that can be accessed from both
GUI components (TextureBrowserPanel) and rendering (Viewport3D).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from PIL import Image

if TYPE_CHECKING:
    import moderngl
    from PyQt6.QtGui import QPixmap

logger = logging.getLogger(__name__)

# Supported texture formats
SUPPORTED_FORMATS = {".tga", ".dds", ".jpg", ".jpeg", ".png", ".bmp"}

# Default thumbnail size
THUMBNAIL_SIZE = (64, 64)


@dataclass
class TextureInfo:
    """
    Information about a texture file.

    Attributes:
        name: Texture name for MAP files (e.g., "metal@bunker_vent")
        path: Full filesystem path to the texture file
        folder: Subfolder relative to texture root (e.g., "europe")
        surface_type: Surface type extracted from @ prefix (e.g., "metal")
        format: File format extension (e.g., "tga", "dds")
        width: Texture width in pixels (0 if not loaded)
        height: Texture height in pixels (0 if not loaded)
    """
    name: str
    path: Path
    folder: str = ""
    surface_type: str = ""
    format: str = ""
    width: int = 0
    height: int = 0

    def __post_init__(self):
        """Extract surface type and format from name/path."""
        # Extract format from path
        if not self.format and self.path:
            self.format = self.path.suffix.lower().lstrip(".")

        # Extract surface type from @ prefix in filename (not full path)
        # e.g., "austria/doors/metal@wood_door" -> surface_type = "metal"
        if not self.surface_type and "@" in self.name:
            # Get filename part only (after last /)
            if "/" in self.name:
                filename = self.name.rsplit("/", 1)[-1]
            else:
                filename = self.name
            # Extract surface type from filename
            if "@" in filename:
                self.surface_type = filename.split("@")[0]


@dataclass
class TextureManager:
    """
    Singleton manager for texture loading and caching.

    Usage:
        manager = TextureManager.instance()
        manager.set_texture_path(Path("C:/CoD/main/textures"))
        manager.scan_textures()

        # Get thumbnail for GUI
        pixmap = manager.get_thumbnail("europe/metal@bunker_vent")

        # Get GPU texture for rendering
        gpu_tex = manager.get_gpu_texture(ctx, "europe/metal@bunker_vent")
    """

    texture_path: Optional[Path] = None

    # Caches
    _texture_info_cache: dict[str, TextureInfo] = field(default_factory=dict)
    _thumbnail_cache: dict[str, "QPixmap"] = field(default_factory=dict)
    _gpu_texture_cache: dict[str, "moderngl.Texture"] = field(default_factory=dict)
    _pil_image_cache: dict[str, Image.Image] = field(default_factory=dict)

    # Folder structure cache
    _folders: list[str] = field(default_factory=list)

    # Singleton instance
    _instance: Optional["TextureManager"] = field(default=None, repr=False)

    @classmethod
    def instance(cls) -> "TextureManager":
        """Get the singleton instance of TextureManager."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing)."""
        if cls._instance is not None:
            cls._instance.clear_cache()
        cls._instance = None

    def set_texture_path(self, path: Path | str) -> None:
        """
        Set the root texture directory path.

        Args:
            path: Path to the texture directory (e.g., "C:/CoD/main/textures")
        """
        self.texture_path = Path(path) if isinstance(path, str) else path
        logger.info(f"Texture path set to: {self.texture_path}")

    def scan_textures(self) -> dict[str, TextureInfo]:
        """
        Scan the texture directory and build the texture info cache.

        Returns:
            Dictionary mapping texture names to TextureInfo objects.
        """
        if not self.texture_path or not self.texture_path.exists():
            logger.warning(f"Texture path does not exist: {self.texture_path}")
            return {}

        logger.info(f"Scanning textures in: {self.texture_path}")

        # Clear existing cache
        self._texture_info_cache.clear()
        self._folders.clear()

        folder_set: set[str] = set()

        # Scan all supported image files
        for ext in SUPPORTED_FORMATS:
            for file_path in self.texture_path.rglob(f"*{ext}"):
                # Get relative path from texture root
                try:
                    rel_path = file_path.relative_to(self.texture_path)
                except ValueError:
                    continue

                # Build texture name (folder/filename without extension)
                # e.g., "europe/metal@bunker_vent"
                full_folder = str(rel_path.parent) if rel_path.parent != Path(".") else ""
                filename = file_path.stem

                if full_folder:
                    texture_name = f"{full_folder}/{filename}"
                else:
                    texture_name = filename

                # Normalize path separators
                texture_name = texture_name.replace("\\", "/")
                full_folder = full_folder.replace("\\", "/")

                # Extract top-level folder (first part only)
                # e.g., "Austria/background" -> "Austria"
                if "/" in full_folder:
                    top_folder = full_folder.split("/")[0]
                else:
                    top_folder = full_folder

                if top_folder:
                    folder_set.add(top_folder)

                # Create TextureInfo with full folder path for filtering
                info = TextureInfo(
                    name=texture_name,
                    path=file_path,
                    folder=full_folder,
                )

                self._texture_info_cache[texture_name] = info

        # Sort folders (only top-level folders)
        self._folders = sorted(folder_set)

        logger.info(
            f"Found {len(self._texture_info_cache)} textures "
            f"in {len(self._folders)} folders"
        )

        return self._texture_info_cache

    def get_texture_info(self, texture_name: str) -> Optional[TextureInfo]:
        """
        Get texture info by name.

        Args:
            texture_name: Texture name (e.g., "europe/metal@bunker_vent")

        Returns:
            TextureInfo or None if not found.
        """
        # Normalize name
        texture_name = texture_name.replace("\\", "/")
        return self._texture_info_cache.get(texture_name)

    def get_texture_folders(self) -> list[str]:
        """
        Get list of texture folders.

        Returns:
            Sorted list of folder names.
        """
        return self._folders.copy()

    def get_textures_in_folder(self, folder: str) -> list[TextureInfo]:
        """
        Get all textures in a specific folder (including subfolders).

        Args:
            folder: Top-level folder name (e.g., "Austria") or "" for root

        Returns:
            List of TextureInfo objects in the folder and its subfolders.
        """
        folder = folder.replace("\\", "/")
        if not folder:
            # Return textures in root (no folder)
            return [
                info for info in self._texture_info_cache.values()
                if not info.folder
            ]

        # Return textures where folder starts with the given folder name
        # This includes "Austria", "Austria/background", "Austria/doors", etc.
        return [
            info for info in self._texture_info_cache.values()
            if info.folder == folder or info.folder.startswith(folder + "/")
        ]

    def search_textures(self, query: str) -> list[TextureInfo]:
        """
        Search textures by name (case-insensitive).

        Args:
            query: Search query string

        Returns:
            List of matching TextureInfo objects.
        """
        query = query.lower()
        return [
            info for info in self._texture_info_cache.values()
            if query in info.name.lower()
        ]

    def get_textures_by_surface_type(self, surface_type: str) -> list[TextureInfo]:
        """
        Get textures by surface type.

        Args:
            surface_type: Surface type (e.g., "metal", "wood", "dirt")

        Returns:
            List of TextureInfo objects with the given surface type.
        """
        surface_type = surface_type.lower()
        return [
            info for info in self._texture_info_cache.values()
            if info.surface_type.lower() == surface_type
        ]

    def get_all_surface_types(self) -> list[str]:
        """
        Get list of all unique surface types.

        Returns:
            Sorted list of surface type names.
        """
        types = {
            info.surface_type for info in self._texture_info_cache.values()
            if info.surface_type
        }
        return sorted(types)

    def get_all_subfolders(self) -> list[str]:
        """
        Get list of all unique subfolder names (second level folders).

        For example, if textures are in:
        - Austria/doors/texture1.tga
        - Egypt/doors/texture2.tga
        - Austria/walls/texture3.tga

        This returns: ["doors", "walls"]

        Returns:
            Sorted list of unique subfolder names.
        """
        subfolders: set[str] = set()
        for info in self._texture_info_cache.values():
            if "/" in info.folder:
                # Get the second part of the path (subfolder)
                parts = info.folder.split("/")
                if len(parts) >= 2:
                    subfolders.add(parts[1])
        return sorted(subfolders)

    def get_textures_by_subfolder(self, subfolder: str) -> list[TextureInfo]:
        """
        Get textures by subfolder name (second level folder).

        This groups textures from different parent folders but same subfolder name.
        E.g., subfolder="doors" returns textures from Austria/doors, Egypt/doors, etc.

        Args:
            subfolder: Subfolder name (e.g., "doors", "walls")

        Returns:
            List of TextureInfo objects in folders ending with the given subfolder.
        """
        subfolder = subfolder.lower()
        result = []
        for info in self._texture_info_cache.values():
            if "/" in info.folder:
                parts = info.folder.split("/")
                if len(parts) >= 2 and parts[1].lower() == subfolder:
                    result.append(info)
        return result

    def _load_image(self, texture_name: str) -> Optional[Image.Image]:
        """
        Load a texture image using PIL.

        Args:
            texture_name: Texture name

        Returns:
            PIL Image or None if loading failed.
        """
        # Check cache first
        if texture_name in self._pil_image_cache:
            return self._pil_image_cache[texture_name]

        info = self.get_texture_info(texture_name)
        if not info:
            logger.warning(f"Texture not found: {texture_name}")
            return None

        try:
            image = Image.open(info.path)

            # Convert to RGBA for consistent handling
            if image.mode != "RGBA":
                image = image.convert("RGBA")

            # Update texture info with dimensions
            info.width = image.width
            info.height = image.height

            # Cache the image
            self._pil_image_cache[texture_name] = image

            return image

        except Exception as e:
            logger.error(f"Failed to load texture {texture_name}: {e}")
            return None

    def get_thumbnail(self, texture_name: str, size: tuple[int, int] = THUMBNAIL_SIZE) -> Optional["QPixmap"]:
        """
        Get a thumbnail QPixmap for GUI display.

        Args:
            texture_name: Texture name
            size: Thumbnail size (width, height)

        Returns:
            QPixmap or None if loading failed.
        """
        from PyQt6.QtGui import QImage, QPixmap

        # Check cache first
        cache_key = f"{texture_name}_{size[0]}x{size[1]}"
        if cache_key in self._thumbnail_cache:
            return self._thumbnail_cache[cache_key]

        # Load the image
        image = self._load_image(texture_name)
        if image is None:
            return None

        try:
            # Create thumbnail
            thumb = image.copy()
            thumb.thumbnail(size, Image.Resampling.LANCZOS)

            # Convert to QPixmap
            data = thumb.tobytes("raw", "RGBA")
            qimage = QImage(
                data,
                thumb.width,
                thumb.height,
                thumb.width * 4,
                QImage.Format.Format_RGBA8888
            )

            pixmap = QPixmap.fromImage(qimage)

            # Cache the thumbnail
            self._thumbnail_cache[cache_key] = pixmap

            return pixmap

        except Exception as e:
            logger.error(f"Failed to create thumbnail for {texture_name}: {e}")
            return None

    def get_gpu_texture(
        self,
        ctx: "moderngl.Context",
        texture_name: str
    ) -> Optional["moderngl.Texture"]:
        """
        Get a GPU texture for 3D rendering.

        Args:
            ctx: ModernGL context
            texture_name: Texture name

        Returns:
            moderngl.Texture or None if loading failed.
        """
        # Check cache first
        if texture_name in self._gpu_texture_cache:
            tex = self._gpu_texture_cache[texture_name]
            # Verify the texture is still valid for this context
            if tex.ctx == ctx:
                return tex
            else:
                # Different context, need to recreate
                del self._gpu_texture_cache[texture_name]

        # Load the image
        image = self._load_image(texture_name)
        if image is None:
            return None

        try:
            # Flip vertically for OpenGL (origin is bottom-left)
            image = image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

            # Create GPU texture
            texture = ctx.texture(
                size=(image.width, image.height),
                components=4,
                data=image.tobytes()
            )

            # Set texture parameters
            texture.filter = (
                ctx.LINEAR_MIPMAP_LINEAR,  # Minification
                ctx.LINEAR  # Magnification
            )
            texture.build_mipmaps()

            # Enable texture repeat (tiling)
            texture.repeat_x = True
            texture.repeat_y = True

            # Enable anisotropic filtering if available
            try:
                texture.anisotropy = 16.0
            except Exception:
                pass  # Not all contexts support anisotropy

            # Cache the texture
            self._gpu_texture_cache[texture_name] = texture

            return texture

        except Exception as e:
            logger.error(f"Failed to create GPU texture for {texture_name}: {e}")
            return None

    def preload_folder(self, folder: str) -> int:
        """
        Preload all textures in a folder into the PIL cache.

        Args:
            folder: Folder name

        Returns:
            Number of textures loaded.
        """
        textures = self.get_textures_in_folder(folder)
        loaded = 0

        for info in textures:
            if self._load_image(info.name):
                loaded += 1

        logger.info(f"Preloaded {loaded}/{len(textures)} textures from {folder}")
        return loaded

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._texture_info_cache.clear()
        self._thumbnail_cache.clear()
        self._pil_image_cache.clear()
        self._folders.clear()

        # Release GPU textures
        for texture in self._gpu_texture_cache.values():
            try:
                texture.release()
            except Exception:
                pass
        self._gpu_texture_cache.clear()

        logger.info("Texture caches cleared")

    def clear_gpu_cache(self) -> None:
        """Clear only the GPU texture cache (for context changes)."""
        for texture in self._gpu_texture_cache.values():
            try:
                texture.release()
            except Exception:
                pass
        self._gpu_texture_cache.clear()

        logger.info("GPU texture cache cleared")

    def get_cache_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache sizes.
        """
        return {
            "texture_info": len(self._texture_info_cache),
            "thumbnails": len(self._thumbnail_cache),
            "pil_images": len(self._pil_image_cache),
            "gpu_textures": len(self._gpu_texture_cache),
            "folders": len(self._folders),
        }

    def __len__(self) -> int:
        """Return the number of textures in the cache."""
        return len(self._texture_info_cache)

    def __contains__(self, texture_name: str) -> bool:
        """Check if a texture exists in the cache."""
        return texture_name.replace("\\", "/") in self._texture_info_cache

    def __iter__(self):
        """Iterate over texture names."""
        return iter(self._texture_info_cache)


# Convenience function to get the singleton instance
def get_texture_manager() -> TextureManager:
    """Get the global TextureManager instance."""
    return TextureManager.instance()


# Base texture axes from Quake/Radiant source (TextureAxisFromPlane)
# Each row: [normal_to_match, s_axis, t_axis]
_BASE_AXES = [
    # floor (Z+)
    ([0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]),
    # ceiling (Z-)
    ([0.0, 0.0, -1.0], [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]),
    # west wall (X+)
    ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]),
    # east wall (X-)
    ([-1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]),
    # south wall (Y+)
    ([0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]),
    # north wall (Y-)
    ([0.0, -1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]),
]


def _texture_axis_from_plane(normal: "np.ndarray") -> tuple["np.ndarray", "np.ndarray"]:
    """
    Get texture axes from plane normal using Quake/Radiant algorithm.

    This matches the TextureAxisFromPlane function from q3map2/map.cpp.
    Finds the best matching base axis and returns the corresponding S and T axes.

    Args:
        normal: Plane normal vector (numpy array)

    Returns:
        Tuple of (s_axis, t_axis) numpy arrays
    """
    import numpy as np

    best_dot = -1.0
    best_axis = 0

    for i, (axis_normal, _, _) in enumerate(_BASE_AXES):
        dot = float(np.dot(normal, axis_normal))
        if dot > best_dot:
            best_dot = dot
            best_axis = i

    _, s_axis, t_axis = _BASE_AXES[best_axis]
    return np.array(s_axis, dtype=np.float64), np.array(t_axis, dtype=np.float64)


def compute_uv(
    vertex: "np.ndarray",
    normal: "np.ndarray",
    offset: tuple[float, float],
    rotation: float,
    scale: tuple[float, float],
    texture_width: int = 256,
    texture_height: int = 256,
) -> tuple[float, float]:
    """
    Compute UV coordinates for a vertex using Quake/Radiant planar projection.

    This implements the QuakeTextureVecs algorithm from q3map2/map.cpp:
    1. Get texture axes from plane normal (TextureAxisFromPlane)
    2. Apply rotation to axes
    3. Apply scale (divide axes by scale factor)
    4. Project vertex onto scaled/rotated axes
    5. Add offset

    Args:
        vertex: 3D vertex position
        normal: Face normal vector
        offset: Texture offset (shift) in texture pixels
        rotation: Texture rotation in degrees
        scale: Texture scale (u, v)
        texture_width: Texture width in pixels (default 256)
        texture_height: Texture height in pixels (default 256)

    Returns:
        Tuple of (u, v) texture coordinates
    """
    import numpy as np
    import math

    # Get base texture axes from plane normal
    s_axis, t_axis = _texture_axis_from_plane(normal)

    # Handle zero scales
    scale_x = scale[0] if abs(scale[0]) > 1e-6 else 1.0
    scale_y = scale[1] if abs(scale[1]) > 1e-6 else 1.0

    # Apply rotation (matches QuakeTextureVecs logic)
    if rotation == 0.0:
        sinv, cosv = 0.0, 1.0
    elif rotation == 90.0:
        sinv, cosv = 1.0, 0.0
    elif rotation == 180.0:
        sinv, cosv = 0.0, -1.0
    elif rotation == 270.0:
        sinv, cosv = -1.0, 0.0
    else:
        angle_rad = math.radians(rotation)
        sinv = math.sin(angle_rad)
        cosv = math.cos(angle_rad)

    # Find which component of the axes is non-zero (sv, tv indices)
    # This determines which axis component gets rotated
    if s_axis[0] != 0:
        sv = 0
    elif s_axis[1] != 0:
        sv = 1
    else:
        sv = 2

    if t_axis[0] != 0:
        tv = 0
    elif t_axis[1] != 0:
        tv = 1
    else:
        tv = 2

    # Apply rotation to both axes
    s_axis_rot = s_axis.copy()
    t_axis_rot = t_axis.copy()

    # Rotate s_axis
    ns = cosv * s_axis[sv] - sinv * s_axis[tv]
    nt = sinv * s_axis[sv] + cosv * s_axis[tv]
    s_axis_rot[sv] = ns
    s_axis_rot[tv] = nt

    # Rotate t_axis
    ns = cosv * t_axis[sv] - sinv * t_axis[tv]
    nt = sinv * t_axis[sv] + cosv * t_axis[tv]
    t_axis_rot[sv] = ns
    t_axis_rot[tv] = nt

    # In Quake/Radiant MAP format:
    # - scale values are in "texture pixels per world unit"
    # - A scale of 0.25 means 4 texture pixels per world unit
    # - UV coordinates are normalized (0-1 = one texture repeat)
    #
    # Formula: u = (vertex dot s_axis) / (scale_x * texture_width) + offset_x / texture_width
    # Simplified: u = (vertex dot s_axis) / scale_x / texture_width + offset_x / texture_width

    # Apply scale - divide axis by scale to get "per texture pixel" projection
    s_axis_scaled = s_axis_rot / scale_x
    t_axis_scaled = t_axis_rot / scale_y

    # Project vertex onto texture axes (result is in texture pixels)
    s = float(np.dot(vertex, s_axis_scaled))
    t = float(np.dot(vertex, t_axis_scaled))

    # Convert to normalized UV coordinates (0-1 range per texture)
    # and add offset (shift is in texture pixels)
    u = (s + offset[0]) / texture_width
    v = (t + offset[1]) / texture_height

    # Invert V coordinate to match OpenGL convention
    # The texture is flipped during loading (FLIP_TOP_BOTTOM), so we need to flip V
    v = -v

    return (u, v)


def compute_face_uvs(
    face_vertices: list["np.ndarray"],
    normal: "np.ndarray",
    offset: tuple[float, float],
    rotation: float,
    scale: tuple[float, float],
    texture_width: int = 256,
    texture_height: int = 256,
) -> list[tuple[float, float]]:
    """
    Compute UV coordinates for all vertices of a face.

    Args:
        face_vertices: List of vertex positions
        normal: Face normal vector
        offset: Texture offset (u, v)
        rotation: Texture rotation in degrees
        scale: Texture scale (u, v)
        texture_width: Texture width in pixels
        texture_height: Texture height in pixels

    Returns:
        List of (u, v) tuples for each vertex
    """
    return [
        compute_uv(v, normal, offset, rotation, scale, texture_width, texture_height)
        for v in face_vertices
    ]
