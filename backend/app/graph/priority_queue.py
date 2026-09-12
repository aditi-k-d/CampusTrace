"""
Priority queue (binary heap) for ranking contacts by risk score.

Python's heapq is a min-heap, so priorities are negated on push to get
max-priority-first pop order. A monotonic counter breaks ties so equal
priorities pop in insertion order (FIFO) rather than comparing items
directly, which would crash on non-comparable items like dicts.
"""

import heapq


class PriorityQueue:
    def __init__(self):
        self._heap: list = []
        self._counter = 0

    def push(self, item, priority: float) -> None:
        heapq.heappush(self._heap, (-priority, self._counter, item))
        self._counter += 1

    def pop(self):
        """Returns (item, priority) with the highest priority, or raises
        IndexError if empty."""
        if not self._heap:
            raise IndexError("pop from empty PriorityQueue")
        neg_priority, _, item = heapq.heappop(self._heap)
        return item, -neg_priority

    def peek(self):
        if not self._heap:
            raise IndexError("peek from empty PriorityQueue")
        neg_priority, _, item = self._heap[0]
        return item, -neg_priority

    def is_empty(self) -> bool:
        return len(self._heap) == 0

    def __len__(self) -> int:
        return len(self._heap)