"""
Risk scoring engine — explainable, rule-based (no black-box ML), per
methodology.md's explicit non-goal on ML risk scoring.

Three pieces:
  1. compute_contact_risk() — single-contact score in [0, 1] combining
     duration (capped), exponential time-decay by recency, and a
     room-type weight (e.g. a lab counts for more than a lecture hall).
  2. aggregate_risk() — combines several contact scores between the
     same pair (ContactEdge is per-occurrence, so a pair can have
     multiple rows) using noisy-OR: treats each contact as an
     independent chance of transmission and computes the probability
     that at least one of them caused exposure. This avoids naive
     summing pushing a score past 100 just because two people crossed
     paths five times in one week.
  3. classify_risk() — buckets a combined score into Low/Medium/High
     against configurable thresholds (feedback.py's false-positive
     loop is what adjusts these over time, per methodology.md).
"""

import math

DEFAULT_DECAY_RATE = 0.15
DEFAULT_DURATION_CAP_MINUTES = 120
DEFAULT_LOW_THRESHOLD = 0.30
DEFAULT_HIGH_THRESHOLD = 0.65


def compute_contact_risk(
    duration_minutes: float,
    days_since_contact: float,
    room_type_weight: float = 1.0,
    decay_rate: float = DEFAULT_DECAY_RATE,
    duration_cap_minutes: float = DEFAULT_DURATION_CAP_MINUTES,
) -> float:
    """Score for a single contact occurrence, in [0, 1]."""
    duration_component = min(max(duration_minutes, 0) / duration_cap_minutes, 1.0)
    recency_component = math.exp(-decay_rate * max(days_since_contact, 0))
    score = duration_component * recency_component * room_type_weight
    return max(0.0, min(score, 1.0))


def aggregate_risk(contact_scores: list[float]) -> float:
    """Noisy-OR combination of several independent contact scores into
    one combined probability of exposure, in [0, 1]."""
    if not contact_scores:
        return 0.0
    survival_probability = 1.0
    for score in contact_scores:
        survival_probability *= (1 - score)
    return 1 - survival_probability


def classify_risk(
    score_0_1: float,
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
) -> str:
    if score_0_1 >= high_threshold:
        return "high"
    if score_0_1 >= low_threshold:
        return "medium"
    return "low"


def score_contact_group(
    contacts: list[dict],
    decay_rate: float = DEFAULT_DECAY_RATE,
    duration_cap_minutes: float = DEFAULT_DURATION_CAP_MINUTES,
    low_threshold: float = DEFAULT_LOW_THRESHOLD,
    high_threshold: float = DEFAULT_HIGH_THRESHOLD,
) -> tuple[float, str]:
    """contacts: list of dicts with keys duration_minutes,
    days_since_contact, and optionally room_type_weight.
    Returns (score out of 100, risk_level)."""
    scores = [
        compute_contact_risk(
            c["duration_minutes"],
            c["days_since_contact"],
            c.get("room_type_weight", 1.0),
            decay_rate,
            duration_cap_minutes,
        )
        for c in contacts
    ]
    combined = aggregate_risk(scores)
    return round(combined * 100, 2), classify_risk(combined, low_threshold, high_threshold)