"""
Graph — weighted adjacency-list graph, built from scratch (no NetworkX).

Represents the contact network: nodes are user IDs, edges are shared
presence events. Kept deliberately generic/DB-agnostic so it's testable
in isolation — services/graph_builder.py is what translates ContactEdge
rows into calls on this class, and tracing_service.py is what decides
which date range of edges to include (that's where "forward" vs
"backward" tracing actually gets realized, not in this file).
"""

from collections import namedtuple, defaultdict

Edge = namedtuple("Edge", ["neighbor", "weight", "attrs"])


class Graph:
    def __init__(self, directed: bool = False):
        self.directed = directed
        self._adjacency: dict[object, list[Edge]] = defaultdict(list)
        self._nodes: set[object] = set()

    def add_node(self, node) -> None:
        self._nodes.add(node)
        # touch the defaultdict so an isolated node still shows up in neighbors()
        _ = self._adjacency[node]

    def add_edge(self, u, v, weight: float = 1.0, **attrs) -> None:
        self.add_node(u)
        self.add_node(v)
        self._adjacency[u].append(Edge(v, weight, attrs))
        if not self.directed:
            self._adjacency[v].append(Edge(u, weight, attrs))

    def has_node(self, node) -> bool:
        return node in self._nodes

    def neighbors(self, node) -> list[Edge]:
        return self._adjacency.get(node, [])

    def nodes(self) -> list:
        return list(self._nodes)

    def degree(self, node) -> int:
        return len(self._adjacency.get(node, []))

    def edge_count(self) -> int:
        total = sum(len(edges) for edges in self._adjacency.values())
        return total if self.directed else total // 2

    def __contains__(self, node) -> bool:
        return self.has_node(node)

    def __repr__(self):
        return f"<Graph nodes={len(self._nodes)} edges={self.edge_count()} directed={self.directed}>"