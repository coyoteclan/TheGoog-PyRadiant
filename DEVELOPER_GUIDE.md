# CoD1 Radiant Editor - Developer Guide

> **Wichtig:** Dieses Dokument muss bei jeder Codeänderung aktualisiert werden!
> Letzte Aktualisierung: 2026-01-07

## Inhaltsverzeichnis

1. [Projektübersicht](#projektübersicht)
2. [Architektur](#architektur)
3. [Modul-Struktur](#modul-struktur)
4. [Coding Guidelines](#coding-guidelines)
5. [Geometrie-System](#geometrie-system)
6. [Event-System](#event-system)
7. [GUI-Komponenten](#gui-komponenten)
8. [I/O-System](#io-system)
9. [Testing](#testing)
10. [Performance-Richtlinien](#performance-richtlinien)
11. [Häufige Fehler vermeiden](#häufige-fehler-vermeiden)

---

## Projektübersicht

CoD1 Radiant ist ein moderner 3D-Level-Editor für Call of Duty 1, kompatibel mit dem `.MAP`-Dateiformat.

### Technologie-Stack

| Komponente | Technologie |
|------------|-------------|
| Sprache | Python 3.11+ |
| GUI Framework | PyQt6 |
| 3D Rendering | ModernGL / OpenGL |
| 2D Rendering | ModernGL (Hardware-beschleunigt) |
| Mathematik | NumPy |

### Projektstruktur

```
cod1radiant/
├── core/               # Kernlogik (GUI-unabhängig)
│   ├── geometry/       # Geometrieklassen
│   ├── operations/     # Geometrie-Operationen
│   ├── map_document.py # Haupt-Dokumentklasse
│   ├── events.py       # Event-Bus-System
│   ├── selection.py    # Selektionsverwaltung
│   └── commands.py     # Undo/Redo-System
├── gui/                # GUI-Komponenten
│   ├── controllers/    # MVC Controller
│   ├── tools/          # Editor-Werkzeuge
│   ├── dialogs/        # Dialoge
│   └── viewport_*.py   # Viewport-Implementierungen
├── io/                 # Datei-I/O
│   ├── map_parser*.py  # MAP-Parser
│   └── map_writer*.py  # MAP-Writer
├── config.py           # Konfiguration
└── main.py             # Einstiegspunkt
```

---

## Architektur

### Schichten-Architektur

```
┌─────────────────────────────────────────┐
│              GUI Layer                  │
│  (MainWindow, Viewports, Panels)        │
├─────────────────────────────────────────┤
│           Controller Layer              │
│  (FileController, EditController, ...)  │
├─────────────────────────────────────────┤
│            Event Bus                    │
│  (Entkoppelte Kommunikation)            │
├─────────────────────────────────────────┤
│            Core Layer                   │
│  (MapDocument, Geometry, Operations)    │
├─────────────────────────────────────────┤
│             I/O Layer                   │
│  (MapParser, MapWriter)                 │
└─────────────────────────────────────────┘
```

### Wichtige Prinzipien

1. **GUI-unabhängiger Core**: `core/` hat keine PyQt-Abhängigkeiten
2. **Event-basierte Kommunikation**: Komponenten kommunizieren über Events
3. **Dataclass-basierte Geometrie**: Immutable wo möglich, explizite Mutation
4. **ID-basierte Referenzen**: Brushes/Entities haben eindeutige IDs

---

## Modul-Struktur

### Core Module

#### `core/geometry/` - Geometrieklassen

```python
# Alle Geometrieklassen importieren:
from cod1radiant.core.geometry import (
    Plane,           # 3-Punkt-Ebene
    BrushFace,       # Basis-Face (Datenklasse)
    Face,            # Erweitertes Face mit Vertices
    Brush,           # Brush mit Methoden
    EdgeOperation,   # Edge-Drag-Operation
    CurveVertex,     # Patch-Vertex
    Curve,           # Kurven-Patch
    Terrain,         # Terrain-Patch
    Patch,           # Legacy Patch-Alias
    PatchVertex,     # Legacy Vertex-Alias
    Entity,          # Entity mit Brushes-Liste
    EntityBase,      # Entity mit brush_ids
)
```

**Klassenhierarchie:**

```
BrushFace (dataclass)
    └── Face (erweitert mit vertices, get_center, get_normal)

BrushBase (dataclass, nur Daten)
    └── Brush (erweitert mit Methoden: translate, rotate, copy, etc.)

EntityBase (dataclass, ID-basiert)
    └── Entity (erweitert mit brushes-Liste)
```

#### `core/operations/` - Funktionale Operationen

```python
from cod1radiant.core.operations import (
    brush_operations,    # get_bounds, get_center, translate, rotate
    entity_operations,   # get_origin, get_angles, get_category
    plane_operations,    # compute_normal, compute_distance
)
```

#### `core/map_document.py` - Dokumentverwaltung

```python
class MapDocument:
    entities: list[Entity]      # Alle Entities
    selection: SelectionManager # Aktuelle Selektion
    command_stack: CommandStack # Undo/Redo

    # Wichtige Methoden:
    def add_entity(entity: Entity)
    def get_brush_by_id(brush_id: int) -> Brush | None
    def iter_brushes() -> Iterator[Brush]
    def get_selected_brushes() -> list[Brush]
```

#### `core/events.py` - Event-System

```python
from cod1radiant.core.events import events, SelectionChangedEvent

# Event publizieren:
events.publish(SelectionChangedEvent(
    selected_brush_ids=frozenset({1, 2, 3}),
    source="viewport_2d"
))

# Event abonnieren:
events.subscribe(SelectionChangedEvent, self._on_selection_changed)
```

### GUI Module

#### Controller (`gui/controllers/`)

| Controller | Verantwortung |
|------------|---------------|
| `FileController` | Laden, Speichern, Recent Files |
| `EditController` | Undo, Redo, Copy, Paste, Delete |
| `ViewController` | Grid, Zoom, View-Modi |
| `BrushController` | Brush-Erstellung, Primitives |

#### Viewports (`gui/viewport_*.py`)

| Viewport | Beschreibung |
|----------|--------------|
| `Viewport2DGL` | Hardware-beschleunigter 2D-Editor |
| `Viewport3D` | 3D-Ansicht mit Kamera |

### I/O Module

```python
# Legacy Parser (für GUI):
from cod1radiant.io import MapParser, MapWriter

# V2 Parser (ID-basiert):
from cod1radiant.io import MapParserV2, MapWriterV2, ParseResult
```

---

## Coding Guidelines

### 1. Importe

```python
# RICHTIG: Aus core importieren
from cod1radiant.core import Brush, Entity, MapDocument
from cod1radiant.core.geometry import Plane, Face

# FALSCH: Direkt aus Untermodulen
from cod1radiant.core.geometry.brush_extended import Brush  # Nicht empfohlen
```

### 2. Type Hints

```python
# Alle Funktionen müssen Type Hints haben
def get_brush_center(brush: Brush) -> np.ndarray:
    """Berechnet den Mittelpunkt eines Brushes."""
    min_pt, max_pt = brush.get_bounds()
    return (min_pt + max_pt) / 2.0
```

### 3. Docstrings

```python
def create_cylinder(
    brush_id: int,
    center: np.ndarray,
    radius: float,
    height: float,
    sides: int = 8
) -> Brush:
    """
    Erstellt einen zylindrischen Brush.

    Args:
        brush_id: Eindeutige Brush-ID
        center: Mittelpunkt der Basis
        radius: Radius des Zylinders
        height: Höhe des Zylinders
        sides: Anzahl der Seiten (min. 3)

    Returns:
        Neuer Brush mit berechneten Vertices

    Raises:
        ValueError: Wenn sides < 3
    """
```

### 4. Event-Kommunikation

```python
# RICHTIG: Events für Komponenten-Kommunikation
events.publish(BrushGeometryModifiedEvent(
    brush_ids=frozenset({brush.id}),
    modification_type="translate"
))

# FALSCH: Direkte Aufrufe zwischen Komponenten
self.main_window.viewport_3d.update()  # Tight coupling!
```

### 5. Geometrie-Änderungen

```python
# Nach jeder Geometrie-Änderung:
brush.translate(offset)
brush.invalidate_cache()  # Cache invalidieren
# ODER:
brush.compute_vertices()  # Vertices neu berechnen
```

### 6. Fehlerbehandlung

```python
def get_brush_by_id(self, brush_id: int) -> Brush | None:
    """Gibt None zurück statt Exception zu werfen."""
    for entity in self.entities:
        for brush in entity.brushes:
            if brush.id == brush_id:
                return brush
    return None  # Nicht gefunden
```

---

## Geometrie-System

### Brush-Struktur

Ein Brush besteht aus mindestens 4 Faces (Flächen), die einen konvexen Körper definieren.

```python
brush = Brush(
    id=1,
    faces=[
        Face(plane=Plane(p1, p2, p3), texture="common/caulk"),
        # ... mindestens 4 Faces
    ]
)
brush.compute_vertices()  # Vertices aus Ebenen-Schnittmengen berechnen
```

### Plane-Definition

Ebenen werden durch 3 Punkte definiert (im Uhrzeigersinn für Innen-Normale):

```python
plane = Plane(
    p1=np.array([0.0, 0.0, 64.0]),
    p2=np.array([0.0, 1.0, 64.0]),
    p3=np.array([1.0, 0.0, 64.0])
)
normal = plane.normal  # Automatisch berechnet
distance = plane.distance
```

### Vertex-Berechnung

Vertices werden durch Schnitt von je 3 Ebenen berechnet:

```python
def compute_vertices(self):
    for i, j, k in combinations(range(len(faces)), 3):
        point = three_plane_intersection(
            face_i.plane, face_j.plane, face_k.plane
        )
        if point is not None and self._is_inside_all_planes(point):
            # Gültiger Vertex
```

### Brush-Erstellung

```python
# Block erstellen
brush = Brush.create_block(
    brush_id=doc.next_brush_id(),
    min_pt=[0, 0, 0],
    max_pt=[64, 64, 64],
    texture="common/caulk"
)

# Zum Worldspawn hinzufügen
doc.add_brush_to_worldspawn(brush)
```

---

## Event-System

### Verfügbare Events

| Event | Beschreibung | Payload |
|-------|--------------|---------|
| `SelectionChangedEvent` | Selektion geändert | brush_ids, entity_ids, source |
| `BrushGeometryModifiedEvent` | Brush-Geometrie geändert | brush_ids, modification_type |
| `EntityGeometryModifiedEvent` | Entity geändert | entity_ids, modification_type |
| `DocumentLoadedEvent` | Dokument geladen | filepath |
| `DocumentModifiedEvent` | Dokument modifiziert | modified (bool) |
| `FilterChangedEvent` | Filter geändert | filters (dict) |
| `GridSizeChangedEvent` | Grid-Größe geändert | grid_size |
| `ViewModeChangedEvent` | 2D-Ansicht gewechselt | axis |
| `ViewportRefreshEvent` | Viewport neu zeichnen | source, refresh_2d, refresh_3d |

### Event-Nutzung

```python
# In __init__ oder setup:
events.subscribe(SelectionChangedEvent, self._on_selection_changed)

# Handler:
def _on_selection_changed(self, event: SelectionChangedEvent):
    if event.source == "viewport_2d":
        return  # Eigenes Event ignorieren
    self._update_selection_display(event.selected_brush_ids)

# Event auslösen:
events.publish(SelectionChangedEvent(
    selected_brush_ids=frozenset(self.selected_ids),
    source="viewport_3d"
))
```

---

## GUI-Komponenten

### MainWindow-Struktur

```python
class MainWindow(QMainWindow):
    # Dokument
    document: MapDocument

    # Viewports
    viewport_2d: Viewport2DGL
    viewport_3d: Viewport3D

    # Controller
    file_controller: FileController
    edit_controller: EditController
    view_controller: ViewController
    brush_controller: BrushController

    # Panels
    brush_properties: BrushPropertiesPanel
    texture_properties: TexturePropertiesPanel
    entity_properties: EntityPropertiesPanel
    filter_panel: FilterPanel
    info_panel: InfoPanel
```

### Neues Panel hinzufügen

1. Panel-Klasse erstellen in `gui/`:
```python
class MyPanel(QWidget):
    my_signal = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def set_document(self, doc: MapDocument):
        self.document = doc
```

2. In `MainWindow._create_docks()` registrieren:
```python
from .my_panel import MyPanel

self._my_dock = QDockWidget("My Panel", self)
self.my_panel = MyPanel()
self._my_dock.setWidget(self.my_panel)
self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._my_dock)
```

### Neuen Controller hinzufügen

1. Controller erstellen in `gui/controllers/`:
```python
class MyController:
    def __init__(self, main_window: "MainWindow"):
        self.main_window = main_window

    @property
    def document(self) -> MapDocument:
        return self.main_window.document
```

2. In `__init__.py` exportieren
3. In `MainWindow._setup_controllers()` initialisieren

---

## I/O-System

### MAP-Datei laden

```python
from cod1radiant.io import MapParser
from cod1radiant.core import MapDocument

parser = MapParser()
doc = MapDocument()

# Parsen
entities = parser.parse_file("map.map")

# Entities zum Dokument hinzufügen
for entity in entities:
    doc.add_entity(entity)
```

### MAP-Datei speichern

```python
from cod1radiant.io import MapWriter

writer = MapWriter()
writer.write_file(doc.entities, "output.map")
```

### V2 Parser (ID-basiert)

```python
from cod1radiant.io import MapParserV2, MapWriterV2

parser = MapParserV2()
result = parser.parse_file("map.map")

# result.entities: list[EntityBase]
# result.brushes: dict[int, BrushBase]
# result.curves: dict[int, Curve]
# result.terrains: dict[int, Terrain]
```

---

## Testing

### Tests ausführen

```bash
# Alle Tests
python -m pytest tests/ -v -p no:dash

# Spezifische Tests
python -m pytest tests/test_geometry.py -v
python -m pytest tests/test_operations.py -v
```

### Test schreiben

```python
# tests/test_my_feature.py
import pytest
from cod1radiant.core import Brush, Entity

class TestMyFeature:
    def test_brush_creation(self):
        brush = Brush.create_block(
            brush_id=1,
            min_pt=[0, 0, 0],
            max_pt=[64, 64, 64]
        )
        assert len(brush.faces) == 6
        assert len(brush.get_all_vertices()) == 8

    def test_bounds(self):
        brush = Brush.create_block(1, [0, 0, 0], [64, 64, 64])
        min_pt, max_pt = brush.get_bounds()
        assert min_pt[0] == pytest.approx(0.0)
        assert max_pt[0] == pytest.approx(64.0)
```

---

## Performance-Richtlinien

### 1. Caching nutzen

```python
# Brush hat internes Caching
brush._vertices_cache   # Gecachte Vertices
brush._bounds_cache     # Gecachte Bounds

# Nach Änderungen invalidieren:
brush.invalidate_cache()
```

### 2. Batch-Operationen

```python
# RICHTIG: Einmal Event für viele Brushes
events.publish(BrushGeometryModifiedEvent(
    brush_ids=frozenset(modified_brush_ids),
    modification_type="batch_translate"
))

# FALSCH: Event pro Brush
for brush in brushes:
    events.publish(BrushGeometryModifiedEvent(
        brush_ids=frozenset({brush.id}),
        ...
    ))
```

### 3. NumPy für Vektoroperationen

```python
# RICHTIG: NumPy-Operationen
vertices = np.array(vertices_list)
center = np.mean(vertices, axis=0)

# FALSCH: Python-Schleifen
center = [0, 0, 0]
for v in vertices:
    center[0] += v[0]
    # ...
```

### 4. Viewport-Updates minimieren

```python
# Nur bei Bedarf updaten
if geometry_changed:
    events.publish(BrushGeometryModifiedEvent(...))
# Nicht:
self.viewport_2d.update()
self.viewport_3d.update()
```

---

## Häufige Fehler vermeiden

### 1. Vergessene Vertex-Berechnung

```python
# FALSCH:
brush = Brush(id=1, faces=faces)
# brush.get_bounds() gibt (0,0,0), (0,0,0) zurück!

# RICHTIG:
brush = Brush(id=1, faces=faces)
brush.compute_vertices()
```

### 2. Zirkuläre Imports

```python
# FALSCH in core/:
from ..gui.main_window import MainWindow  # GUI in Core!

# RICHTIG: TYPE_CHECKING verwenden
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..gui.main_window import MainWindow
```

### 3. Direkte Attributzugriffe

```python
# FALSCH:
doc.entities[0].brushes[0].faces[0].texture = "new"
doc.modified = True

# RICHTIG: Methoden verwenden
brush = doc.get_brush_by_id(brush_id)
if brush:
    brush.faces[0].texture = "new"
    doc.modified = True
```

### 4. Event-Schleifen

```python
def _on_selection_changed(self, event):
    # FALSCH: Löst neues Event aus -> Endlosschleife!
    self.select_brush(event.brush_ids)

    # RICHTIG: Source prüfen
    if event.source == self.__class__.__name__:
        return  # Eigenes Event ignorieren
```

### 5. Fehlende Cache-Invalidierung

```python
# FALSCH:
brush.faces[0].plane.p1 += offset
# Cache ist jetzt ungültig!

# RICHTIG:
brush.translate(offset)  # Methode invalidiert Cache automatisch
# ODER:
brush.faces[0].plane.p1 += offset
brush.invalidate_cache()
brush.compute_vertices()
```

---

## Changelog

### 2026-01-07 - Initial Release
- Projekt-Refactoring abgeschlossen
- Legacy-Code entfernt (brush.py, patch.py, entity.py, conversion.py, map_document_v2.py)
- Saubere Geometrie-Hierarchie in `core/geometry/`
- Event-basierte Kommunikation implementiert
- 45 Tests bestehen

---

## Kontakt

Bei Fragen zur Architektur oder Code-Qualität: Markdown 'Issue_NAME' im Verzeichnis erstellen.
