"""
Unit tests for app/graph/* — the hand-written DSA modules.
Run: cd backend && pytest app/tests/test_graph.py -v
"""

import pytest

from app.graph.graph import Graph
from app.graph.traversal import bfs, dfs, trace_forward, trace_backward
from app.graph.union_find import UnionFind
from app.graph.priority_queue import PriorityQueue
from app.graph.risk_engine import (
    compute_contact_risk,
    aggregate_risk,
    classify_risk,
    score_contact_group,
)


# --- Graph ---

@pytest.fixture()
def sample_graph():
    g = Graph()
    g.add_edge("A", "B", weight=1.0)
    g.add_edge("B", "C", weight=2.0)
    g.add_edge("C", "D", weight=1.0)
    g.add_edge("A", "E", weight=5.0)
    return g


def test_graph_node_and_edge_counts(sample_graph):
    assert len(sample_graph.nodes()) == 5
    assert sample_graph.edge_count() == 4  # undirected: 4 add_edge calls -> 4 logical edges


def test_graph_degree_and_neighbors(sample_graph):
    assert sample_graph.degree("A") == 2
    assert {e.neighbor for e in sample_graph.neighbors("B")} == {"A", "C"}


def test_graph_is_undirected_by_default(sample_graph):
    # an edge added as A->B must be traversable B->A too
    assert any(e.neighbor == "A" for e in sample_graph.neighbors("B"))


def test_graph_isolated_node_has_no_neighbors():
    g = Graph()
    g.add_node("solo")
    assert g.neighbors("solo") == []
    assert g.has_node("solo")


# --- BFS / DFS ---

def test_bfs_reaches_all_connected_nodes(sample_graph):
    result = bfs(sample_graph, "A")
    assert set(result.keys()) == {"A", "B", "C", "D", "E"}


def test_bfs_computes_correct_shortest_depth(sample_graph):
    result = bfs(sample_graph, "A")
    assert result["D"]["depth"] == 3  # A -> B -> C -> D


def test_bfs_respects_max_depth(sample_graph):
    result = bfs(sample_graph, "A", max_depth=1)
    assert set(result.keys()) == {"A", "B", "E"}


def test_dfs_reaches_all_connected_nodes(sample_graph):
    result = dfs(sample_graph, "A")
    assert set(result.keys()) == {"A", "B", "C", "D", "E"}


def test_bfs_on_missing_start_returns_empty(sample_graph):
    assert bfs(sample_graph, "not_in_graph") == {}


def test_trace_forward_excludes_source_node(sample_graph):
    traced = trace_forward(sample_graph, "A", max_depth=2)
    assert "A" not in traced


def test_trace_forward_respects_depth_limit(sample_graph):
    traced = trace_forward(sample_graph, "A", max_depth=2)
    assert "D" not in traced  # D is depth 3
    assert "B" in traced and "C" in traced


def test_trace_backward_same_shape_as_forward(sample_graph):
    traced = trace_backward(sample_graph, "A", max_depth=1)
    assert set(traced.keys()) == {"B", "E"}


# --- Union-Find ---

def test_union_find_transitive_connectivity():
    uf = UnionFind()
    uf.union("s1", "s2")
    uf.union("s2", "s3")
    assert uf.connected("s1", "s3")


def test_union_find_separate_groups_not_connected():
    uf = UnionFind()
    uf.union("s1", "s2")
    uf.union("s4", "s5")
    assert not uf.connected("s1", "s4")


def test_union_find_clusters_exclude_singletons():
    uf = UnionFind()
    uf.union("s1", "s2")
    uf.union("s2", "s3")
    uf.union("s4", "s5")
    uf.make_set("s6")  # isolated, never unioned

    clusters = [set(c) for c in uf.clusters()]
    assert {"s1", "s2", "s3"} in clusters
    assert {"s4", "s5"} in clusters
    assert not any("s6" in c for c in clusters)


# --- PriorityQueue ---

def test_priority_queue_pops_highest_priority_first():
    pq = PriorityQueue()
    pq.push("low", 20)
    pq.push("high", 90)
    pq.push("medium", 55)

    assert pq.pop() == ("high", 90)
    assert pq.pop() == ("medium", 55)
    assert pq.pop() == ("low", 20)


def test_priority_queue_equal_priority_is_fifo():
    pq = PriorityQueue()
    pq.push("first_in", 50)
    pq.push("second_in", 50)

    assert pq.pop()[0] == "first_in"
    assert pq.pop()[0] == "second_in"


def test_priority_queue_pop_on_empty_raises():
    pq = PriorityQueue()
    with pytest.raises(IndexError):
        pq.pop()


def test_priority_queue_len_and_is_empty():
    pq = PriorityQueue()
    assert pq.is_empty()
    pq.push("x", 1)
    assert len(pq) == 1
    assert not pq.is_empty()


# --- risk_engine ---

def test_recent_long_contact_scores_higher_than_old_short_one():
    recent_long = compute_contact_risk(duration_minutes=120, days_since_contact=0, room_type_weight=1.2)
    old_short = compute_contact_risk(duration_minutes=10, days_since_contact=10, room_type_weight=1.2)
    assert recent_long > old_short


def test_contact_risk_is_capped_at_one():
    assert compute_contact_risk(duration_minutes=500, days_since_contact=0, room_type_weight=2.0) <= 1.0


def test_aggregate_risk_single_score_unchanged():
    assert aggregate_risk([0.5]) == pytest.approx(0.5)


def test_aggregate_risk_noisy_or_combination():
    # 1 - (1-0.5)*(1-0.5) = 0.75
    assert aggregate_risk([0.5, 0.5]) == pytest.approx(0.75)


def test_aggregate_risk_never_exceeds_one():
    assert aggregate_risk([0.9] * 10) <= 1.0


def test_aggregate_risk_empty_list_is_zero():
    assert aggregate_risk([]) == 0.0


def test_classify_risk_thresholds():
    assert classify_risk(0.1) == "low"
    assert classify_risk(0.5) == "medium"
    assert classify_risk(0.8) == "high"


def test_score_contact_group_returns_valid_range_and_level():
    contacts = [
        {"duration_minutes": 90, "days_since_contact": 1, "room_type_weight": 1.2},
        {"duration_minutes": 45, "days_since_contact": 4, "room_type_weight": 1.0},
    ]
    score, level = score_contact_group(contacts)
    assert 0 <= score <= 100
    assert level in ("low", "medium", "high")