"""
Capacity service — priority-queue bed allocation.

Uses app/graph/priority_queue.py's PriorityQueue (the project's
hand-written binary-heap implementation) to rank waiting users by their
highest Alert.risk_score and allocate a bed to whichever user has the
greatest need.

Design notes:
- "Waiting" = has an unacknowledged, unallocated Alert with a non-zero
  risk_score and no active IsolationAllocation yet.
- A user can only hold one active allocation at a time (released_at IS
  NULL check).  allocate_bed() is idempotent for already-allocated users:
  it silently skips them rather than creating a second row.
- When no bed is free, allocate_bed() returns None without error —
  the route layer decides how to surface that to the caller.
"""

from datetime import datetime, timezone

from app.extensions import db
from app.graph.priority_queue import PriorityQueue
from app.models.alert import Alert
from app.models.capacity import Capacity, IsolationAllocation


def _active_allocation(user_id: int) -> bool:
    """True if the user already holds an unreleased bed."""
    return IsolationAllocation.query.filter_by(
        user_id=user_id, released_at=None
    ).first() is not None


def build_waiting_queue() -> PriorityQueue:
    """Scan Alert rows for users who need a bed and haven't been allocated
    one yet.  Each user's priority = their highest risk_score across all
    their active alerts.  Returns a PriorityQueue ready to pop."""
    pq = PriorityQueue()

    # Pull every alert not yet acknowledged (and therefore still actionable),
    # group by user and keep the highest risk_score per user.
    from sqlalchemy import func
    rows = (
        db.session.query(Alert.user_id, func.max(Alert.risk_score))
        .filter(Alert.acknowledged_at.is_(None))
        .group_by(Alert.user_id)
        .all()
    )

    for user_id, max_score in rows:
        if not _active_allocation(user_id):
            pq.push({"user_id": user_id}, float(max_score))

    return pq


def allocate_bed(capacity: Capacity, user_id: int, risk_score: float) -> IsolationAllocation | None:
    """Allocate one bed in `capacity` for `user_id` at the given risk_score.

    Returns the new IsolationAllocation (unflushed/uncommitted — caller
    must commit) or None if the facility is already full or the user already
    holds an active allocation.
    """
    if capacity.occupied_beds >= capacity.total_beds:
        return None
    if _active_allocation(user_id):
        return None

    allocation = IsolationAllocation(
        user_id=user_id,
        capacity_id=capacity.id,
        priority_score=risk_score,
    )
    capacity.occupied_beds += 1
    db.session.add(allocation)
    return allocation


def allocate_highest_priority(capacity: Capacity) -> IsolationAllocation | None:
    """Pull the highest-priority waiting user from the global queue and
    allocate them a bed in `capacity`.

    Returns the new IsolationAllocation or None when:
    - the facility is full, or
    - nobody is currently waiting (queue empty).
    Caller must commit after a non-None return.
    """
    if capacity.occupied_beds >= capacity.total_beds:
        return None

    pq = build_waiting_queue()
    if pq.is_empty():
        return None

    user_info, risk_score = pq.pop()
    return allocate_bed(capacity, user_info["user_id"], risk_score)


def release_bed(allocation: IsolationAllocation) -> None:
    """Mark an allocation as released and decrement occupied count.
    Caller must commit."""
    if allocation.released_at is None:
        allocation.released_at = datetime.now(timezone.utc)
        allocation.capacity.occupied_beds = max(0, allocation.capacity.occupied_beds - 1)


def get_waiting_queue_ranked() -> list[dict]:
    """Drain build_waiting_queue() in priority order (highest risk_score first)
    and return a ranked list of dicts.

    Each entry: {rank, user_id, priority_score}

    build_waiting_queue() constructs a fresh PriorityQueue per call (no global
    state), so draining it here has no side effects on the allocation state.
    """
    pq = build_waiting_queue()
    ranked: list[dict] = []
    rank = 1
    while not pq.is_empty():
        user_info, priority_score = pq.pop()
        ranked.append({
            "rank": rank,
            "user_id": user_info["user_id"],
            "priority_score": round(float(priority_score), 2),
        })
        rank += 1
    return ranked

