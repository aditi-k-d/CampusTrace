"""
Tracing service — wraps graph/traversal.py for use by routes.

Two design decisions worth knowing:

1. Subgraphs are pulled incrementally, hop by hop, scoped to only the
   nodes actually being expanded — never "load the whole contact
   graph". At institution scale this is the difference between a
   query bounded by (max_depth x average degree) and one that scans
   every ContactEdge in the database.

2. 'Forward' vs 'backward' is realized entirely by which ContactEdge
   rows get pulled into the Graph (on/after onset date vs before it) —
   traversal.py's bfs()/dfs() have no idea which direction they're
   being used for. That split lives here, not in the DSA layer.

Risk scoring for a traced contact uses the edge connecting them to
their immediate BFS parent (a real, dated contact event) rather than
the cumulative path weight. Contacts found beyond the first hop get
an additional per-hop confidence decay, since a 2nd-degree contact's
exposure is inherently less certain than a direct one.
"""

from datetime import date as date_cls

from app.extensions import db
from app.models import ContactEdge, SystemConfig, HealthRecord
from app.graph.graph import Graph
from app.graph.traversal import trace_forward, trace_backward
from app.graph.risk_engine import compute_contact_risk, classify_risk

HOP_CONFIDENCE_DECAY = 0.5  # each additional hop beyond the direct contact halves confidence


def _query_edges_touching(user_ids: set[int], date_predicate):
    if not user_ids:
        return []
    query = ContactEdge.query.filter(
        db.or_(ContactEdge.user_a_id.in_(user_ids), ContactEdge.user_b_id.in_(user_ids))
    )
    query = date_predicate(query)
    return query.all()


def _build_bounded_graph(source_id: int, max_depth: int, date_predicate) -> Graph:
    """Expands the graph outward from source_id, one hop at a time,
    querying only the frontier nodes discovered so far."""
    graph = Graph()
    graph.add_node(source_id)
    visited = {source_id}
    frontier = {source_id}

    for _ in range(max_depth):
        edges = _query_edges_touching(frontier, date_predicate)
        next_frontier = set()
        for edge in edges:
            graph.add_edge(
                edge.user_a_id,
                edge.user_b_id,
                weight=float(edge.room_type_weight),
                duration_minutes=edge.duration_minutes,
                contact_date=edge.contact_date,
            )
            for node in (edge.user_a_id, edge.user_b_id):
                if node not in visited:
                    next_frontier.add(node)
        visited |= next_frontier
        frontier = next_frontier
        if not frontier:
            break

    return graph


def _score_traced(traced: dict, graph: Graph, reference_date: date_cls,
                  low_threshold: float, high_threshold: float) -> dict:
    """Score each traced contact and include per-edge detail for visualization.

    Each contact entry now contains:
      depth, risk_score, risk_level, contact_type ("direct" | "indirect"),
      duration_minutes, contact_date, days_since_contact,
      room_type_weight, hop_decay, base_score
    """
    scored = {}
    for node, info in traced.items():
        parent = info["parent"]
        depth = info["depth"]

        edge_attrs = None
        edge_weight = 1.0
        for edge in graph.neighbors(parent):
            if edge.neighbor == node:
                edge_attrs = edge.attrs
                edge_weight = edge.weight
                break
        if edge_attrs is None:
            continue  # shouldn't happen, but don't let one bad node break the batch

        contact_date = edge_attrs["contact_date"]
        days_since = abs((reference_date - contact_date).days)
        base_score = compute_contact_risk(
            duration_minutes=edge_attrs["duration_minutes"],
            days_since_contact=days_since,
            room_type_weight=edge_weight,
        )
        hop_decay = HOP_CONFIDENCE_DECAY ** (depth - 1)
        combined_score = base_score * hop_decay

        scored[node] = {
            "depth": depth,
            "risk_score": round(combined_score * 100, 2),
            "risk_level": classify_risk(combined_score, low_threshold, high_threshold),
            # Edge detail — surfaced for visualization and analytics breakdown
            "contact_type": "direct" if depth == 1 else "indirect",
            "duration_minutes": edge_attrs["duration_minutes"],
            "contact_date": str(contact_date),
            "days_since_contact": days_since,
            "room_type_weight": round(edge_weight, 4),
            "hop_decay": round(hop_decay, 4),
            "base_score": round(base_score * 100, 2),
        }
    return scored


def _build_graph_payload(source_id: int, all_contacts: dict) -> dict:
    """Build a vis-network-compatible nodes/edges payload from the combined
    forward+backward contact maps.

    Nodes:  {id, is_source, depth, risk_score, risk_level}
    Edges:  {source, target, duration_minutes, contact_date, weight}
    """
    node_map: dict[int, dict] = {
        source_id: {
            "id": source_id,
            "is_source": True,
            "depth": 0,
            "risk_score": None,
            "risk_level": "source",
        }
    }
    edge_set: list[dict] = []

    for direction_contacts in all_contacts.values():
        for user_id, info in direction_contacts.items():
            if user_id not in node_map:
                node_map[user_id] = {
                    "id": user_id,
                    "is_source": False,
                    "depth": info["depth"],
                    "risk_score": info["risk_score"],
                    "risk_level": info["risk_level"],
                }
            edge_set.append({
                "source": source_id if info["depth"] == 1 else None,  # simplified; parent unavailable here
                "target": user_id,
                "duration_minutes": info.get("duration_minutes"),
                "contact_date": info.get("contact_date"),
                "weight": info.get("room_type_weight"),
            })

    return {
        "nodes": list(node_map.values()),
        "edges": edge_set,
    }


def trace_case(health_record: HealthRecord, direction: str | None = None, max_depth: int | None = None) -> dict:
    """direction: 'forward' | 'backward' | 'both'. Defaults come from
    SystemConfig (Institute Admin's global tracing settings) but can be
    overridden per-case, per methodology.md ("configurable per outbreak
    rather than hardcoded").

    Risk thresholds are read from SystemConfig so Health Admin's
    feedback-review adjustments take effect immediately on the next
    trace, without changing risk_engine.py's own constants.

    Returns:
      {
        "forward": {user_id: {...scored...}},   # if direction in forward/both
        "backward": {user_id: {...scored...}},  # if direction in backward/both
        "graph": {"nodes": [...], "edges": [...]},
      }
    """
    config = SystemConfig.get()
    direction = direction or config.default_tracing_direction
    max_depth = max_depth or config.default_tracing_depth

    # Float cast: Numeric columns come back as Decimal from SQLAlchemy.
    low_threshold = float(config.risk_low_threshold)
    high_threshold = float(config.risk_high_threshold)

    source_id = health_record.user_id
    onset = health_record.onset_date
    results = {}

    if direction in ("forward", "both"):
        fwd_predicate = lambda q: q.filter(ContactEdge.contact_date >= onset)
        fwd_graph = _build_bounded_graph(source_id, max_depth, fwd_predicate)
        fwd_traced = trace_forward(fwd_graph, source_id, max_depth)
        results["forward"] = _score_traced(fwd_traced, fwd_graph, onset, low_threshold, high_threshold)

    if direction in ("backward", "both"):
        bwd_predicate = lambda q: q.filter(ContactEdge.contact_date < onset)
        bwd_graph = _build_bounded_graph(source_id, max_depth, bwd_predicate)
        bwd_traced = trace_backward(bwd_graph, source_id, max_depth)
        results["backward"] = _score_traced(bwd_traced, bwd_graph, onset, low_threshold, high_threshold)

    results["graph"] = _build_graph_payload(source_id, {
        k: v for k, v in results.items() if k != "graph"
    })

    return results


def get_case_risk_breakdown(health_record: HealthRecord) -> list[dict]:
    """Return a flat list of contact risk-breakdown entries suitable for the
    analytics breakdown view.  Calls trace_case() internally and reshapes —
    no scoring is recomputed here.

    Each entry:
      {user_id, direction, depth, contact_type, duration_minutes,
       contact_date, days_since_contact, room_type_weight, hop_decay,
       base_score, risk_score, risk_level}
    """
    trace_result = trace_case(health_record)
    breakdown: list[dict] = []

    for direction in ("forward", "backward"):
        contacts = trace_result.get(direction, {})
        for user_id, info in contacts.items():
            breakdown.append({
                "user_id": user_id,
                "direction": direction,
                "depth": info["depth"],
                "contact_type": info["contact_type"],
                "duration_minutes": info.get("duration_minutes"),
                "contact_date": info.get("contact_date"),
                "days_since_contact": info.get("days_since_contact"),
                "room_type_weight": info.get("room_type_weight"),
                "hop_decay": info.get("hop_decay"),
                "base_score": info.get("base_score"),
                "risk_score": info["risk_score"],
                "risk_level": info["risk_level"],
            })

    # Sort by risk_score descending so the breakdown table leads with highest risk
    breakdown.sort(key=lambda x: x["risk_score"], reverse=True)
    return breakdown