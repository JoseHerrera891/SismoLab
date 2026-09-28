"""
Explicit Stack and Queue implementations for Undo management and Report Processing.
All comments are written in English according to project guidelines.
"""

from collections import deque

class UndoStack:
    """
    Stack (LIFO - Last In, First Out) for handling undo history (Sections 2 & 13).
    Stores previous system states or reversible command objects.
    """
    def __init__(self):
        self._items = []

    def push(self, state):
        """Pushes a new state onto the top of the stack."""
        self._items.append(state)

    def pop(self):
        """Removes and returns the top state from the stack."""
        if self.is_empty():
            raise IndexError("Cannot pop from an empty UndoStack.")
        return self._items.pop()

    def peek(self):
        """Returns the top element without removing it."""
        if self.is_empty():
            return None
        return self._items[-1]

    def is_empty(self) -> bool:
        """Checks if the stack is empty."""
        return len(self._items) == 0

    def size(self) -> int:
        """Returns total items in the stack."""
        return len(self._items)

    def clear(self):
        """Clears all history in the stack."""
        self._items.clear()


class ReportQueue:
    """
    Queue (FIFO - First In, First Out) for managing incoming report bursts (Sections 2 & 8).
    Reports are processed strictly in the order they were received.
    """
    def __init__(self):
        self._items = deque()

    def enqueue(self, report_data: dict):
        """Adds a new incoming report to the end of the queue."""
        self._items.append(report_data)

    def dequeue(self) -> dict:
        """Removes and returns the oldest report at the front of the queue."""
        if self.is_empty():
            raise IndexError("Cannot dequeue from an empty ReportQueue.")
        return self._items.popleft()

    def is_empty(self) -> bool:
        """Checks if there are pending reports in the queue."""
        return len(self._items) == 0

    def size(self) -> int:
        """Returns the number of pending reports."""
        return len(self._items)

    def to_list(self) -> list:
        """Returns a snapshot list of current items for GUI rendering."""
        return list(self._items)