# CoD1 Map Parser

Vollständiger Parser für das Call of Duty 1 `.map` Dateiformat. Alle Map-Elemente sind individuell adressierbar und modifizierbar.

## Installation

Keine externen Abhängigkeiten erforderlich.

```python
# Modularer Import (empfohlen)
from cod1_map import parse_map_file, CoD1Map, Vec3

# Oder einzelne Datei
from cod1_map_parser import *
```

## Paket-Struktur

```
cod1_map/
├── __init__.py     # Package exports
├── math.py         # Vec3, Color
├── types.py        # BrushType, ContentFlag, TextureParams, PatchParams
├── patch.py        # PatchVertex, Patch
├── brush.py        # BrushPlane, Brush
├── entity.py       # Entity
├── map.py          # CoD1Map, Helper-Funktionen
└── parser.py       # CoD1MapParser, parse_map_file, parse_map_string
```

## Schnellstart

```python
from cod1_map import parse_map_file, Vec3

# Map laden
map_data = parse_map_file("path/to/map.map")

# Worldspawn zugreifen
worldspawn = map_data.worldspawn

# Alle Brushes durchgehen
for brush in worldspawn.brushes:
    if brush.is_regular:
        print(f"Regular Brush mit {brush.plane_count} Planes")
    elif brush.is_terrain:
        print(f"Terrain Patch: {brush.patch.rows}x{brush.patch.cols}")
    elif brush.is_curve:
        print(f"Curve Patch: {brush.patch.rows}x{brush.patch.cols}")

# Map speichern
map_data.save("output.map")
```

## Datenmodell

### Hierarchie

```
CoD1Map
├── entities: List[Entity]
│   ├── Entity 0 (worldspawn)
│   │   ├── properties: Dict[str, str]
│   │   └── brushes: List[Brush]
│   │       ├── Brush (REGULAR) - Plane-basierte Geometrie
│   │       │   └── planes: List[BrushPlane]
│   │       │       └── BrushPlane
│   │       │           ├── point1, point2, point3: Vec3
│   │       │           ├── shader: str
│   │       │           └── texture: TextureParams
│   │       ├── Brush (TERRAIN) - patchTerrainDef3
│   │       │   └── patch: Patch
│   │       │       ├── shader: str
│   │       │       ├── params: PatchParams
│   │       │       └── vertices: List[List[PatchVertex]]
│   │       └── Brush (CURVE) - patchDef5
│   │           └── patch: Patch
│   ├── Entity 1..N
│   │   ├── properties: Dict[str, str]
│   │   └── brushes: List[Brush] (optional)
│   └── ...
```

### Brush-Typen

| Typ | Format | Beschreibung |
|-----|--------|--------------|
| **REGULAR** | Plane-Definitionen | Konvexe Volumenkörper aus mindestens 4 Ebenen (Wände, Böden, Kisten) |
| **TERRAIN** | `patchTerrainDef3` | Terrain-Mesh mit Vertex-Grid (Gelände, Hügel) |
| **CURVE** | `patchDef5` | Bezier-Kurven/Flächen (Bögen, Rohre, organische Formen) |

**Total Brushes = Regular + Terrain + Curves**

## Klassen-Referenz

### CoD1Map

Hauptcontainer für die gesamte Map.

```python
class CoD1Map:
    entities: List[Entity]
    filepath: str

    # Properties
    worldspawn: Entity
    entity_count: int
    total_brush_count: int
    world_brush_count: int

    # Methoden
    get_entity(index: int) -> Optional[Entity]
    add_entity(entity: Entity) -> None
    remove_entity(index: int) -> Optional[Entity]
    get_entities_by_classname(classname: str) -> List[Entity]
    get_point_entities() -> List[Entity]
    get_brush_entities() -> List[Entity]
    get_all_brushes() -> List[Brush]
    get_world_brushes() -> List[Brush]
    get_all_regular_brushes() -> List[Brush]
    get_all_terrain_patches() -> List[Brush]
    get_all_curve_patches() -> List[Brush]
    get_all_shaders() -> List[str]
    get_all_classnames() -> List[str]
    get_statistics() -> Dict[str, Any]
    to_map_string() -> str
    save(filepath: str) -> None
    copy() -> CoD1Map
```

### Entity

Eine Entity mit Properties und optionalen Brushes.

```python
class Entity:
    index: int
    properties: Dict[str, str]
    brushes: List[Brush]

    # Properties
    classname: str
    is_worldspawn: bool
    has_brushes: bool
    is_point_entity: bool
    is_brush_entity: bool
    brush_count: int
    origin: Optional[Vec3]
    angles: Optional[Vec3]
    targetname: Optional[str]
    target: Optional[str]
    model: Optional[str]

    # Methoden
    get_property(key: str, default: str = "") -> str
    set_property(key: str, value: str) -> None
    has_property(key: str) -> bool
    remove_property(key: str) -> Optional[str]
    get_brush(index: int) -> Optional[Brush]
    add_brush(brush: Brush) -> None
    remove_brush(index: int) -> Optional[Brush]
    get_regular_brushes() -> List[Brush]
    get_terrain_patches() -> List[Brush]
    get_curve_patches() -> List[Brush]
    get_all_shaders() -> List[str]
    to_map_string() -> str
    copy() -> Entity
```

### Brush

Ein Brush kann entweder ein regulärer Brush (Plane-basiert) oder ein Patch (Terrain/Curve) sein.

```python
class Brush:
    index: int
    brush_type: BrushType
    planes: List[BrushPlane]
    patch: Optional[Patch]

    # Properties
    is_regular: bool
    is_terrain: bool
    is_curve: bool
    is_patch: bool
    plane_count: int
    is_valid: bool

    # Methoden
    get_plane(index: int) -> Optional[BrushPlane]
    add_plane(plane: BrushPlane) -> None
    remove_plane(index: int) -> Optional[BrushPlane]
    get_shaders() -> List[str]
    get_primary_shader() -> str
    set_all_shaders(shader: str) -> None
    get_content_flags() -> int
    set_content_flags(flags: int) -> None
    get_bounding_box() -> Tuple[Vec3, Vec3]
    get_center() -> Vec3
    translate(offset: Vec3) -> None
    to_map_string() -> str
    copy() -> Brush
```

### BrushPlane

Eine einzelne Brush-Plane definiert durch 3 Punkte.

```python
class BrushPlane:
    point1: Vec3
    point2: Vec3
    point3: Vec3
    shader: str
    texture: TextureParams

    # Properties
    normal: Vec3
    distance: float
    content_flags: int
    surface_flags: int

    # Methoden
    get_points() -> Tuple[Vec3, Vec3, Vec3]
    set_points(p1: Vec3, p2: Vec3, p3: Vec3) -> None
    translate(offset: Vec3) -> None
    is_tool_shader() -> bool
    to_map_string() -> str
    copy() -> BrushPlane
```

### Patch

Ein Patch (Terrain-Mesh oder Bezier-Curve).

```python
class Patch:
    patch_type: BrushType
    shader: str
    params: PatchParams
    vertices: List[List[PatchVertex]]  # [row][col]

    # Properties
    rows: int
    cols: int
    vertex_count: int
    is_terrain: bool
    is_curve: bool
    type_name: str

    # Methoden
    get_vertex(row: int, col: int) -> Optional[PatchVertex]
    set_vertex(row: int, col: int, vertex: PatchVertex) -> bool
    get_vertex_position(row: int, col: int) -> Optional[Vec3]
    set_vertex_position(row: int, col: int, position: Vec3) -> bool
    get_vertex_height(row: int, col: int) -> Optional[float]
    set_vertex_height(row: int, col: int, height: float) -> bool
    get_all_vertices() -> List[PatchVertex]
    get_bounding_box() -> Tuple[Vec3, Vec3]
    get_center() -> Vec3
    translate(offset: Vec3) -> None
    scale(factor: float, center: Optional[Vec3] = None) -> None
    to_map_string() -> str
    copy() -> Patch
```

### PatchVertex

Ein einzelner Vertex in einem Patch.

```python
class PatchVertex:
    position: Vec3
    uv: Tuple[float, float]
    color: Color
    turned_edge: int  # 0 oder 1

    # Properties
    x, y, z: float
    u, v: float

    # Methoden
    to_map_string() -> str
    copy() -> PatchVertex

    @classmethod
    from_values(x, y, z, u=0, v=0, r=255, g=255, b=255, a=255, turned_edge=0) -> PatchVertex
```

#### turned_edge Flag

Das `turned_edge` Feld (0 oder 1) kontrolliert die Triangulierung des Quads rechts/unterhalb dieses Vertex:

```
turned_edge=0 (Standard):        turned_edge=1 (Gedreht):
Diagonale v00-v11                Diagonale v01-v10

v00 ──── v01                     v00 ──── v01
 │ ╲      │                       │      ╱ │
 │   ╲    │                       │    ╱   │
 │     ╲  │                       │  ╱     │
v10 ──── v11                     v10 ──── v11
```

**Verwendung:**
```python
vertex = patch.vertices[row][col]
if vertex.turned_edge == 1:
    # Diagonale geht von v01 nach v10
else:
    # Diagonale geht von v00 nach v11 (Standard)
```

**Nur relevant für Terrain-Patches (`patchTerrainDef3`)**, nicht für Bezier-Curves (`patchDef5`).

### Vec3

3D-Vektor für Koordinaten und Richtungen.

```python
class Vec3:
    x: float
    y: float
    z: float

    # Operatoren
    __add__, __sub__
    __mul__, __truediv__
    __neg__
    __eq__, __hash__

    # Methoden
    dot(other: Vec3) -> float
    cross(other: Vec3) -> Vec3
    length() -> float
    normalize() -> Vec3
    copy() -> Vec3
    to_tuple() -> Tuple[float, float, float]
    to_string(precision: int = 6) -> str

    @classmethod
    from_string(s: str) -> Vec3
    @classmethod
    zero() -> Vec3
    @classmethod
    one() -> Vec3
```

## CoD1 Map Format

### Dateistruktur

```
// entity 0
{
"classname" "worldspawn"
"ambient" "0.18"
// brush 0
{
( x1 y1 z1 ) ( x2 y2 z2 ) ( x3 y3 z3 ) shader offset_x offset_y rotation scale_x scale_y content_flags surface_flags value 0
( ... )
}
// brush 1
{
patchTerrainDef3
{
shader_name
( rows cols contents 0 0 0 subdivision )
(
( ( x y z u v r g b a 0 ) ( ... ) )
( ( x y z u v r g b a 0 ) ( ... ) )
)
}
}
}
// entity 1
{
"classname" "light"
"origin" "64 64 128"
}
```

### Brush-Plane Format

```
( X1 Y1 Z1 ) ( X2 Y2 Z2 ) ( X3 Y3 Z3 ) shader offset_x offset_y rotation scale_x scale_y content_flags surface_flags value 0
```

| Parameter | Beschreibung |
|-----------|--------------|
| X1 Y1 Z1, etc. | 3 Punkte die die Plane definieren |
| shader | Textur/Material-Name |
| offset_x, offset_y | Textur-Offset |
| rotation | Textur-Rotation (Grad) |
| scale_x, scale_y | Textur-Skalierung (Standard: 0.25) |
| content_flags | Kollisions-Flags |
| surface_flags | Oberflächen-Flags |
| value | Zusatzwert (meist 0) |

### Patch-Vertex Format

```
( x y z u v r g b alpha turned_edge )
```

| Feld | Beschreibung |
|------|--------------|
| x, y, z | 3D-Position |
| u, v | Textur-Koordinaten |
| r, g, b | Vertex-Farbe (0-255) |
| alpha | Transparenz (0-255) |
| turned_edge | Diagonalen-Richtung für Terrain (0=Standard, 1=Gedreht) |

**Hinweis:** Das `turned_edge` Feld war früher als "reserviert" dokumentiert, ist aber für Terrain-Patches (`patchTerrainDef3`) relevant. Es bestimmt, welche Diagonale beim Triangulieren des Quads verwendet wird. Für Bezier-Curves (`patchDef5`) ist es immer 0.

### Content-Flags

| Wert | Name | Beschreibung |
|------|------|--------------|
| 0 | STRUCTURAL | Standard-Kollision, verursacht BSP-Splitting |
| 134217728 | DETAIL | Detail-Brush, kein BSP-Split |
| 134217732 | NON_COLLIDING | Keine Kollision (DETAIL + 4) |
| 134226048 | WEAPON_CLIP | Waffen-Clip (DETAIL + 8320) |
| 134226052 | WEAPON_CLIP_DETAIL | NON_COLLIDING + WEAPON_CLIP kombiniert |

### Shader-Namenskonvention

**Standard-Texturen mit Surface-Type:**
```
surfacetype@texturname
metal@bunker_vent
wood@floorplank
brick@wall_damaged
concrete@floor
```

**Tool-Shader:**
```
common/caulk         # Unsichtbar (für verdeckte Flächen)
common/clip          # Unsichtbare Kollision
common/nodraw        # Nicht gerendert
common/trigger       # Trigger-Volumen
common/origin        # Origin-Brush
```

## Hilfsfunktionen

### Map parsen

```python
from cod1_map import parse_map_file, parse_map_string

# Von Datei
map_data = parse_map_file("path/to/map.map")

# Von String
map_data = parse_map_string(content)
```

### Objekte erstellen

```python
from cod1_map import create_brush_box, create_terrain_patch, create_entity, Vec3

# Box-Brush erstellen
brush = create_brush_box(
    mins=Vec3(0, 0, 0),
    maxs=Vec3(128, 128, 64),
    shader="brick@wall"
)

# Terrain-Patch erstellen
patch = create_terrain_patch(
    shader="grass@field",
    rows=9,
    cols=9,
    origin=Vec3(0, 0, 0),
    spacing=64.0
)

# Entity erstellen
entity = create_entity(
    classname="info_player_start",
    origin=Vec3(100, 200, 32),
    angles="0 90 0"
)
```

## Beispiele

### Alle Texturen auflisten

```python
map_data = parse_map_file("mymap.map")
shaders = map_data.get_all_shaders()
for shader in shaders:
    print(shader)
```

### Terrain-Höhen modifizieren

```python
ws = map_data.worldspawn
for brush in ws.get_terrain_patches():
    patch = brush.patch
    for row in range(patch.rows):
        for col in range(patch.cols):
            vertex = patch.get_vertex(row, col)
            vertex.position.z *= 2  # Höhe verdoppeln
```

### Terrain-Triangulierung mit turned_edge

```python
# Terrain-Patch triangulieren (für Rendering oder Export)
ws = map_data.worldspawn
for brush in ws.get_terrain_patches():
    patch = brush.patch
    triangles = []

    for row in range(patch.rows - 1):
        for col in range(patch.cols - 1):
            # Quad-Ecken
            v00 = patch.vertices[row][col]
            v01 = patch.vertices[row][col + 1]
            v10 = patch.vertices[row + 1][col]
            v11 = patch.vertices[row + 1][col + 1]

            # turned_edge bestimmt die Diagonale
            if v00.turned_edge == 0:
                # Standard-Diagonale: v00-v11
                triangles.append((v00, v10, v11))
                triangles.append((v00, v11, v01))
            else:
                # Gedrehte Diagonale: v01-v10
                triangles.append((v00, v10, v01))
                triangles.append((v10, v11, v01))

    print(f"Patch {patch.rows}x{patch.cols}: {len(triangles)} Dreiecke")
```

### Alle Lichter finden

```python
lights = map_data.get_entities_by_classname("light")
for light in lights:
    origin = light.origin
    intensity = light.get_property("light", "300")
    print(f"Light at {origin}, intensity={intensity}")
```

### Neuen Spawn-Punkt hinzufügen

```python
spawn = create_entity(
    classname="mp_deathmatch_spawn",
    origin=Vec3(512, 256, 32),
    angles="0 180 0"
)
map_data.add_entity(spawn)
map_data.save("modified.map")
```

### Map-Statistiken

```python
stats = map_data.get_statistics()
print(f"Entities: {stats['entity_count']}")
print(f"Total Brushes: {stats['total_brush_count']}")
print(f"  Regular: {stats['regular_brush_count']}")
print(f"  Terrain: {stats['terrain_patch_count']}")
print(f"  Curves: {stats['curve_patch_count']}")
```

## Validierung

```python
from cod1_map import CoD1MapParser, parse_map_file

parser = CoD1MapParser()
map_data = parse_map_file("mymap.map")
is_valid, errors = parser.validate(map_data)

if not is_valid:
    for error in errors:
        print(f"Error: {error}")
```

## Getestete Maps

| Map | Entities | Brushes | Regular | Terrain | Curves | Shaders |
|-----|----------|---------|---------|---------|--------|---------|
| gg_harbor | 403 | 4,873 | 4,492 | 16 | 365 | 148 |
| cod2_mp_brecourt | 940 | 3,785 | 2,057 | 1,714 | 14 | 58 |
| cod2_mp_burgundy | 627 | 3,902 | 3,067 | 434 | 401 | 99 |
| cod2_mp_carentan | 1,371 | 10,060 | 7,536 | 1,589 | 935 | 119 |
| jtgz_mini_harbor | 232 | 2,385 | 2,227 | 2 | 156 | 101 |

Alle Maps: **Validation PASSED**

## Entity-Typen (Auswahl)

### Worldspawn Properties
- `ambient` - Umgebungslicht
- `sundirection` - Sonnenrichtung (pitch yaw roll)
- `suncolor` - Sonnenfarbe (RGB)
- `sunlight` - Sonnenlicht-Intensität

### Point Entities
- `light` - Lichtquelle
- `info_player_start` - Spawn-Punkt
- `misc_model` - 3D-Modell
- `mp_deathmatch_spawn` - MP-Spawn

### Brush Entities
- `func_door` - Tür
- `func_rotating` - Rotierendes Objekt
- `trigger_multiple` - Trigger

## Lizenz

MIT License
