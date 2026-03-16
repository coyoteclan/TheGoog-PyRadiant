"""
CoD1 Map Parser - Parser Module
===============================

Parser for reading and writing CoD1 .map files.
"""

from __future__ import annotations
import re
from typing import List, Optional, Tuple

from .math import Vec3, Color
from .types import BrushType, TextureParams, PatchParams
from .brush import Brush, BrushPlane
from .patch import Patch, PatchVertex
from .entity import Entity
from .map import CoD1Map


class CoD1MapParser:
    """
    Parser for CoD1 .map files.

    Parses the complete map structure including:
    - Entities with all properties
    - Regular brushes with plane definitions
    - Terrain patches (patchTerrainDef3)
    - Curve patches (patchDef5)

    Usage:
        parser = CoD1MapParser()
        map_data = parser.parse_file("path/to/map.map")
        # or
        map_data = parser.parse(map_content_string)
    """

    # Regex patterns
    PLANE_PATTERN = re.compile(
        r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
        r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
        r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\)\s*'
        r'(\S+)\s*(.*)'
    )

    PROPERTY_PATTERN = re.compile(r'"([^"]*)"\s+"([^"]*)"')

    VERTEX_PATTERN = re.compile(
        r'\(\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+'
        r'([-\d.]+)\s+([-\d.]+)\s+'
        r'(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*\)'
    )

    def __init__(self):
        self._content: str = ""
        self._pos: int = 0
        self._line: int = 1

    def parse_file(self, filepath: str) -> CoD1Map:
        """Parse a .map file from disk."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        map_data = self.parse(content)
        map_data.filepath = filepath
        return map_data

    def parse(self, content: str) -> CoD1Map:
        """Parse .map content from string."""
        self._content = content
        self._pos = 0
        self._line = 1

        map_data = CoD1Map()

        while self._pos < len(self._content):
            self._skip_whitespace_and_comments()

            if self._pos >= len(self._content):
                break

            # Look for entity
            if self._peek_string("// entity") or self._peek_char() == '{':
                entity = self._parse_entity(len(map_data.entities))
                if entity:
                    map_data.entities.append(entity)
            else:
                self._advance()

        return map_data

    # -------------------------------------------------------------------------
    # Internal parsing methods
    # -------------------------------------------------------------------------

    def _peek_char(self) -> str:
        """Peek at current character."""
        if self._pos < len(self._content):
            return self._content[self._pos]
        return ''

    def _peek_string(self, s: str) -> bool:
        """Check if string appears at current position."""
        return self._content[self._pos:self._pos + len(s)] == s

    def _advance(self, count: int = 1) -> str:
        """Advance position and return consumed characters."""
        result = self._content[self._pos:self._pos + count]
        for c in result:
            if c == '\n':
                self._line += 1
        self._pos += count
        return result

    def _skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self._pos < len(self._content) and self._content[self._pos] in ' \t\n\r':
            if self._content[self._pos] == '\n':
                self._line += 1
            self._pos += 1

    def _skip_whitespace_and_comments(self) -> None:
        """Skip whitespace and comments (except entity/brush markers)."""
        while self._pos < len(self._content):
            self._skip_whitespace()

            if self._pos >= len(self._content):
                break

            if self._peek_string('//'):
                # Keep entity and brush comments
                if self._peek_string('// entity') or self._peek_string('// brush'):
                    break
                # Skip other comments
                while self._pos < len(self._content) and self._content[self._pos] != '\n':
                    self._pos += 1
            else:
                break

    def _read_line(self) -> str:
        """Read until end of line."""
        start = self._pos
        while self._pos < len(self._content) and self._content[self._pos] != '\n':
            self._pos += 1
        result = self._content[start:self._pos]
        if self._pos < len(self._content):
            self._pos += 1
            self._line += 1
        return result

    def _parse_entity(self, entity_index: int) -> Optional[Entity]:
        """Parse a complete entity."""
        entity = Entity(index=entity_index)

        self._skip_whitespace_and_comments()

        # Check for entity comment
        if self._peek_string('// entity'):
            line = self._read_line()
            match = re.search(r'// entity (\d+)', line)
            if match:
                entity.index = int(match.group(1))

        self._skip_whitespace_and_comments()

        # Expect opening brace
        if self._peek_char() != '{':
            return None
        self._advance()

        brush_index = 0

        while self._pos < len(self._content):
            self._skip_whitespace_and_comments()

            if self._peek_char() == '}':
                self._advance()
                break

            # Brush comment
            if self._peek_string('// brush'):
                brush = self._parse_brush(brush_index)
                if brush:
                    entity.brushes.append(brush)
                    brush_index += 1
            # Brush without comment
            elif self._peek_char() == '{':
                brush = self._parse_brush(brush_index)
                if brush:
                    entity.brushes.append(brush)
                    brush_index += 1
            # Property
            elif self._peek_char() == '"':
                line = self._read_line()
                match = self.PROPERTY_PATTERN.match(line)
                if match:
                    key, value = match.groups()
                    entity.properties[key] = value
            else:
                self._read_line()

        return entity

    def _parse_brush(self, brush_index: int) -> Optional[Brush]:
        """Parse a complete brush."""
        brush = Brush(index=brush_index)

        self._skip_whitespace_and_comments()

        # Check for brush comment
        if self._peek_string('// brush'):
            line = self._read_line()
            match = re.search(r'// brush (\d+)', line)
            if match:
                brush.index = int(match.group(1))

        self._skip_whitespace_and_comments()

        # Expect opening brace
        if self._peek_char() != '{':
            return None
        self._advance()

        self._skip_whitespace_and_comments()

        # Check for patch type
        if self._peek_string('patchTerrainDef3'):
            brush.brush_type = BrushType.TERRAIN
            brush.patch = self._parse_patch(BrushType.TERRAIN)
        elif self._peek_string('patchDef5'):
            brush.brush_type = BrushType.CURVE
            brush.patch = self._parse_patch(BrushType.CURVE)
        else:
            # Regular brush with planes
            brush.brush_type = BrushType.REGULAR
            while self._pos < len(self._content):
                self._skip_whitespace()

                if self._peek_char() == '}':
                    break

                if self._peek_char() == '(':
                    plane = self._parse_plane()
                    if plane:
                        brush.planes.append(plane)
                else:
                    self._read_line()

        # Find closing brace
        self._skip_whitespace_and_comments()
        if self._peek_char() == '}':
            self._advance()

        return brush if brush.is_valid else None

    def _parse_plane(self) -> Optional[BrushPlane]:
        """Parse a brush plane definition."""
        line = self._read_line()
        match = self.PLANE_PATTERN.match(line.strip())

        if not match:
            return None

        groups = match.groups()

        point1 = Vec3(float(groups[0]), float(groups[1]), float(groups[2]))
        point2 = Vec3(float(groups[3]), float(groups[4]), float(groups[5]))
        point3 = Vec3(float(groups[6]), float(groups[7]), float(groups[8]))
        shader = groups[9]
        params_str = groups[10].strip() if groups[10] else ""

        texture = TextureParams.from_parts(params_str.split()) if params_str else TextureParams()

        return BrushPlane(
            point1=point1,
            point2=point2,
            point3=point3,
            shader=shader,
            texture=texture
        )

    def _parse_patch(self, patch_type: BrushType) -> Optional[Patch]:
        """Parse a patch definition."""
        # Skip patch type keyword
        self._read_line()

        self._skip_whitespace_and_comments()

        # Expect opening brace
        if self._peek_char() != '{':
            return None
        self._advance()

        self._skip_whitespace()

        # Read shader
        shader = self._read_line().strip()

        self._skip_whitespace()

        # Read parameters
        params_line = self._read_line().strip()
        params = PatchParams.from_string(params_line)

        # Parse vertices
        vertices: List[List[PatchVertex]] = []

        self._skip_whitespace()

        # Expect opening paren for vertex section
        if self._peek_char() == '(':
            self._advance()

            while self._pos < len(self._content):
                self._skip_whitespace()

                if self._peek_char() == ')':
                    self._advance()
                    break

                if self._peek_char() == '(':
                    row = self._parse_vertex_row()
                    if row:
                        vertices.append(row)
                else:
                    self._read_line()

        self._skip_whitespace()

        # Find closing brace
        if self._peek_char() == '}':
            self._advance()

        patch = Patch(
            patch_type=patch_type,
            shader=shader,
            params=params,
            vertices=vertices
        )

        return patch

    def _parse_vertex_row(self) -> List[PatchVertex]:
        """Parse a row of vertices."""
        line = self._read_line()
        vertices = []

        for match in self.VERTEX_PATTERN.finditer(line):
            vertex = PatchVertex(
                position=Vec3(
                    float(match.group(1)),
                    float(match.group(2)),
                    float(match.group(3))
                ),
                uv=(float(match.group(4)), float(match.group(5))),
                color=Color(
                    int(match.group(6)),
                    int(match.group(7)),
                    int(match.group(8)),
                    int(match.group(9))
                ),
                turned_edge=int(match.group(10))  # Edge direction flag for diagonal
            )
            vertices.append(vertex)

        return vertices

    def validate(self, map_data: CoD1Map) -> Tuple[bool, List[str]]:
        """
        Validate a parsed map.

        Returns:
            (is_valid, list_of_errors)
        """
        errors = []

        # Check for worldspawn
        if not map_data.worldspawn:
            errors.append("No worldspawn entity found")
        elif map_data.worldspawn.index != 0:
            errors.append("Worldspawn is not entity 0")

        # Check entities
        for entity in map_data.entities:
            if not entity.classname:
                errors.append(f"Entity {entity.index}: Missing classname")

            # Check brushes
            for brush in entity.brushes:
                if brush.is_regular and brush.plane_count < 4:
                    errors.append(f"Entity {entity.index}, Brush {brush.index}: "
                                  f"Invalid brush (only {brush.plane_count} planes, need at least 4)")

                if brush.is_patch and not brush.patch:
                    errors.append(f"Entity {entity.index}, Brush {brush.index}: "
                                  f"Patch brush has no patch data")

        return len(errors) == 0, errors


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def parse_map_file(filepath: str) -> CoD1Map:
    """
    Parse a .map file.

    Args:
        filepath: Path to the .map file

    Returns:
        CoD1Map object
    """
    parser = CoD1MapParser()
    return parser.parse_file(filepath)


def parse_map_string(content: str) -> CoD1Map:
    """
    Parse .map content from string.

    Args:
        content: .map file content as string

    Returns:
        CoD1Map object
    """
    parser = CoD1MapParser()
    return parser.parse(content)
