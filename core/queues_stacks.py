#queus and stacks models for report and undo actions

from collections import deque

class UndoStack:
    #stack for undo, it reverses to a previous state
    def __init__(self):
        self._items = []

    def push(self, state):
        #pushes a new state in the stack
        self._items.append(state)

    def pop(self):
        #removes and returns the last state in the stack
        if self.is_empty():
            raise IndexError("Cannot undo. No previous state.")
        return self._items.pop()

    def peek(self):
        #returns the top state without pop it from the stack
        if self.is_empty():
            return None
        return self._items[-1]

        #normal things, checks if its empty and the size
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)

    def clear(self):
        #this clears the stack
        self._items.clear()


#resport queue, for processing the events in order
class ReportQueue:
    
    def __init__(self):
        self._items = deque()

    def enqueue(self, report_data: dict):
        #for adding a new report
        self._items.append(report_data)

    def dequeue(self) -> dict:
        #returns and eliminates the oldest report from the queue
        if self.is_empty():
            raise IndexError("Cannot process without a report.")
        return self._items.popleft()

    
        #nomral things again
    def is_empty(self) -> bool:
        return len(self._items) == 0

    def size(self) -> int:
        return len(self._items)

    def to_list(self) -> list:
        #returns a list of the reports in line
        return list(self._items)