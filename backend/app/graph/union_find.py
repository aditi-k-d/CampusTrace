"""
Union-Find (Disjoint Set Union) with path compression + union by rank.

Used for outbreak cluster detection: two contacts get union()'d
together when an edge between them is classified as high-risk, and
find() afterward groups everyone into mutually-connected clusters —
this is what feeds the Health Admin's hotspot view.
"""

from collections import defaultdict


class UnionFind:
    def __init__(self):
        self._parent: dict = {}
        self._rank: dict = {}

    def make_set(self, x) -> None:
        if x not in self._parent:
            self._parent[x] = x
            self._rank[x] = 0

    def find(self, x):
        self.make_set(x)
        if self._parent[x] != x:
            self._parent[x] = self.find(self._parent[x])  # path compression
        return self._parent[x]

    def union(self, x, y) -> None:
        root_x, root_y = self.find(x), self.find(y)
        if root_x == root_y:
            return
        if self._rank[root_x] < self._rank[root_y]:
            root_x, root_y = root_y, root_x
        self._parent[root_y] = root_x
        if self._rank[root_x] == self._rank[root_y]:
            self._rank[root_x] += 1

    def connected(self, x, y) -> bool:
        return self.find(x) == self.find(y)

    def clusters(self) -> list[list]:
        """Returns all clusters with more than one member (a singleton
        isn't an outbreak cluster)."""
        groups = defaultdict(list)
        for x in self._parent:
            groups[self.find(x)].append(x)
        return [members for members in groups.values() if len(members) > 1]