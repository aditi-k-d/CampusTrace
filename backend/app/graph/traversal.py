"""
BFS / DFS traversal over graph.Graph — hand-written, depth-bounded.

Both bfs() and dfs() return the same shape: {node: {depth, parent,
path_weight}}. Which one 'forward' vs 'backward' tracing uses is a
choice made by tracing_service.py — it builds two different Graph
instances (edges on/after the case's onset date for forward tracing,
edges before onset for backward tracing) and calls the same traversal
functions on each. Keeping that split out of this file is what makes
these functions pure and unit-testable in isolation.
"""

from collections import deque


def bfs(graph, start, max_depth: int | None = None) -> dict:
    if not graph.has_node(start):
        return {}

    visited = {start: {"depth": 0, "parent": None, "path_weight": 0.0}}
    queue = deque([start])

    while queue:
        current = queue.popleft()
        current_depth = visited[current]["depth"]
        if max_depth is not None and current_depth >= max_depth:
            continue
        for edge in graph.neighbors(current):
            if edge.neighbor not in visited:
                visited[edge.neighbor] = {
                    "depth": current_depth + 1,
                    "parent": current,
                    "path_weight": visited[current]["path_weight"] + edge.weight,
                }
                queue.append(edge.neighbor)

    return visited


def dfs(graph, start, max_depth: int | None = None) -> dict:
    if not graph.has_node(start):
        return {}

    visited = {start: {"depth": 0, "parent": None, "path_weight": 0.0}}
    stack = [start]

    while stack:
        current = stack.pop()
        current_depth = visited[current]["depth"]
        if max_depth is not None and current_depth >= max_depth:
            continue
        for edge in graph.neighbors(current):
            if edge.neighbor not in visited:
                visited[edge.neighbor] = {
                    "depth": current_depth + 1,
                    "parent": current,
                    "path_weight": visited[current]["path_weight"] + edge.weight,
                }
                stack.append(edge.neighbor)

    return visited


def _trace(graph, start, max_depth, method: str) -> dict:
    fn = bfs if method == "bfs" else dfs
    result = fn(graph, start, max_depth)
    result.pop(start, None)  # exclude the source case itself from its own contact list
    return result


def trace_forward(graph, start, max_depth: int | None = None, method: str = "bfs") -> dict:
    """Trace who the source case may have exposed. Assumes `graph` was
    built from contact edges on/after the case's infectious start date —
    that filtering happens in tracing_service.py, not here."""
    return _trace(graph, start, max_depth, method)


def trace_backward(graph, start, max_depth: int | None = None, method: str = "bfs") -> dict:
    """Trace who may have exposed the source case. Assumes `graph` was
    built from contact edges before the case's onset date."""
    return _trace(graph, start, max_depth, method)