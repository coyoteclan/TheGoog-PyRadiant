"""
Command Pattern for Undo/Redo functionality.

Each user action that modifies the document should be wrapped in a Command.
The CommandStack manages execution, undo, and redo.

Usage:
    class TranslateBrushCommand(Command):
        def __init__(self, brush: Brush, offset: Vec3):
            self.brush = brush
            self.offset = offset

        def execute(self):
            self.brush.translate(self.offset)

        def undo(self):
            self.brush.translate(-self.offset)

        @property
        def description(self) -> str:
            return "Translate Brush"

    # Use with document
    doc.execute_command(TranslateBrushCommand(brush, Vec3(10, 0, 0)))
    doc.undo()  # Reverts translation
    doc.redo()  # Re-applies translation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .events import events, UndoRedoEvent

if TYPE_CHECKING:
    from .document import MapDocument


class Command(ABC):
    """
    Abstract base class for undoable commands.

    Subclasses must implement:
    - execute(): Perform the action
    - undo(): Reverse the action
    - description: Human-readable description
    """

    @abstractmethod
    def execute(self) -> None:
        """Execute the command."""
        pass

    @abstractmethod
    def undo(self) -> None:
        """Undo the command."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description for UI."""
        pass

    def redo(self) -> None:
        """
        Redo the command.

        Default implementation calls execute().
        Override if redo differs from initial execution.
        """
        self.execute()


@dataclass
class CommandStack:
    """
    Manages undo/redo stack of commands.

    Attributes:
        max_size: Maximum number of commands to keep in history
    """

    max_size: int = 100
    _undo_stack: list[Command] = field(default_factory=list)
    _redo_stack: list[Command] = field(default_factory=list)

    def execute(self, command: Command) -> None:
        """
        Execute a command and add to undo stack.

        Clears the redo stack since we're starting a new action chain.

        Args:
            command: The command to execute
        """
        command.execute()
        self._undo_stack.append(command)
        self._redo_stack.clear()

        # Limit stack size
        while len(self._undo_stack) > self.max_size:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """
        Undo the last command.

        Returns:
            True if undo was performed, False if nothing to undo
        """
        if not self._undo_stack:
            return False

        command = self._undo_stack.pop()
        command.undo()
        self._redo_stack.append(command)

        events.publish(UndoRedoEvent(
            action="undo",
            description=command.description
        ))

        return True

    def redo(self) -> bool:
        """
        Redo the last undone command.

        Returns:
            True if redo was performed, False if nothing to redo
        """
        if not self._redo_stack:
            return False

        command = self._redo_stack.pop()
        command.redo()
        self._undo_stack.append(command)

        events.publish(UndoRedoEvent(
            action="redo",
            description=command.description
        ))

        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return len(self._redo_stack) > 0

    def clear(self) -> None:
        """Clear both undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()

    @property
    def undo_description(self) -> str | None:
        """Description of next undo action."""
        if self._undo_stack:
            return self._undo_stack[-1].description
        return None

    @property
    def redo_description(self) -> str | None:
        """Description of next redo action."""
        if self._redo_stack:
            return self._redo_stack[-1].description
        return None

    @property
    def undo_count(self) -> int:
        """Number of available undo steps."""
        return len(self._undo_stack)

    @property
    def redo_count(self) -> int:
        """Number of available redo steps."""
        return len(self._redo_stack)


# =============================================================================
# Common Command Implementations
# =============================================================================

@dataclass
class TranslateBrushCommand(Command):
    """Command to translate a brush."""

    from ..io.map_parser.brush import Brush
    from ..io.map_parser.math import Vec3

    brush: "Brush"
    offset: "Vec3"

    def execute(self) -> None:
        self.brush.translate(self.offset)

    def undo(self) -> None:
        self.brush.translate(-self.offset)

    @property
    def description(self) -> str:
        return "Move Brush"


@dataclass
class DeleteBrushCommand(Command):
    """Command to delete a brush from an entity."""

    from ..io.map_parser.brush import Brush
    from ..io.map_parser.entity import Entity

    entity: "Entity"
    brush_index: int
    _deleted_brush: "Brush | None" = field(default=None, init=False)

    def execute(self) -> None:
        self._deleted_brush = self.entity.remove_brush(self.brush_index)

    def undo(self) -> None:
        if self._deleted_brush:
            # Re-insert at original index
            self.entity.brushes.insert(self.brush_index, self._deleted_brush)
            # Reindex brushes
            for i, brush in enumerate(self.entity.brushes):
                brush.index = i

    @property
    def description(self) -> str:
        return "Delete Brush"


@dataclass
class CreateBrushCommand(Command):
    """Command to create a new brush in an entity."""

    from ..io.map_parser.brush import Brush
    from ..io.map_parser.entity import Entity

    entity: "Entity"
    brush: "Brush"
    _brush_index: int = field(default=-1, init=False)

    def execute(self) -> None:
        self.entity.add_brush(self.brush)
        self._brush_index = self.brush.index

    def undo(self) -> None:
        if self._brush_index >= 0:
            self.entity.remove_brush(self._brush_index)

    @property
    def description(self) -> str:
        return "Create Brush"


@dataclass
class CompoundCommand(Command):
    """Command that groups multiple commands together."""

    commands: list[Command]
    _description: str = "Multiple Changes"

    def execute(self) -> None:
        for cmd in self.commands:
            cmd.execute()

    def undo(self) -> None:
        # Undo in reverse order
        for cmd in reversed(self.commands):
            cmd.undo()

    @property
    def description(self) -> str:
        return self._description
