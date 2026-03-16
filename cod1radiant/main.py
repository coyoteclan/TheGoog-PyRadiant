"""Entry point for CoD1 Radiant Editor."""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports
_root = Path(__file__).parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))


def main():
    """Main entry point."""
    # Check for --info flag to show map info
    if len(sys.argv) > 1 and sys.argv[1] == "--info":
        if len(sys.argv) > 2:
            map_path = Path(sys.argv[2])
            if map_path.exists():
                load_and_show_map(map_path)
            else:
                print(f"File not found: {map_path}")
                sys.exit(1)
        else:
            print("Usage: python -m cod1radiant.main --info <mapfile.map>")
        return

    # Launch GUI
    launch_gui()


def load_and_show_map(filepath: Path):
    """Load a MAP file and show its contents."""
    from cod1radiant.io.map_parser import MapParser, MapParseError
    from cod1radiant.io.map_writer import MapWriter

    try:
        parser = MapParser()
        doc = parser.parse_file(filepath)

        print(f"Loaded: {filepath}")
        print()
        print(f"Entities: {len(doc.entities)}")

        total_brushes = sum(len(e.brushes) for e in doc.entities)
        print(f"Total brushes: {total_brushes}")
        print()

        # Show entity summary
        print("Entity Summary:")
        print("-" * 40)

        for entity in doc.entities:
            brush_info = f" ({len(entity.brushes)} brushes)" if entity.brushes else ""
            origin_info = ""
            if entity.origin is not None:
                o = entity.origin
                origin_info = f" @ ({o[0]:.0f}, {o[1]:.0f}, {o[2]:.0f})"
            print(f"  {entity.classname}{brush_info}{origin_info}")

        print()

        # Show worldspawn brushes info
        if doc.worldspawn and doc.worldspawn.brushes:
            bounds = doc.get_bounds()
            if bounds:
                min_pt, max_pt = bounds
                size = max_pt - min_pt
                print(f"Map bounds: ({min_pt[0]:.0f}, {min_pt[1]:.0f}, {min_pt[2]:.0f})")
                print(f"         to ({max_pt[0]:.0f}, {max_pt[1]:.0f}, {max_pt[2]:.0f})")
                print(f"       size: {size[0]:.0f} x {size[1]:.0f} x {size[2]:.0f}")

    except MapParseError as e:
        print(f"Parse error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


def launch_gui():
    """Launch the GUI application."""
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt

    from cod1radiant.gui.main_window import MainWindow

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("CoD1 Radiant")
    app.setOrganizationName("CoD1Radiant")

    # Set dark theme style
    app.setStyle("Fusion")

    # Create and show main window
    window = MainWindow()

    # Load file if provided as argument
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
        if filepath.exists() and filepath.suffix.lower() == '.map':
            window._open_file(str(filepath))

    window.show()

    # Run the event loop
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
