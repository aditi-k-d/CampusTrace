"""
Disease KB service — symptom matching and CRUD helpers.

Symptom matching is deliberately rule-based (keyword overlap), keeping
the same "no black-box ML" policy used by risk_engine.py.  Scoring:
  1. Tokenise both the candidate's `symptoms` field and the incoming
     free-text `custom_symptoms` into lowercased alphabetic words.
  2. Score = |intersection| / |query_tokens| (Jaccard-style recall).
     Recall-biased rather than precision-biased because a patient may
     only mention a subset of a disease's full symptom list.
  3. Return the best match if its score clears a configurable minimum
     (default 0.20 — at least one-fifth of the query words must appear).
     Return None when nothing clears the bar.

CRUD helpers are thin wrappers that let routes stay declarative and
keep validation logic in one place.
"""

import re
from typing import Optional

from app.extensions import db
from app.models.disease_kb import DiseaseKB

# Minimum recall fraction to suggest a match.
MATCH_MIN_SCORE = 0.20


def _tokenize(text: str) -> set[str]:
    """Lower-case alphabetic words only — ignores punctuation/numbers."""
    return set(re.findall(r"[a-z]+", text.lower()))


def suggest_disease(custom_symptoms: str) -> Optional[DiseaseKB]:
    """Return the best-matching DiseaseKB entry for a free-text symptom
    string, or None if no entry clears MATCH_MIN_SCORE."""
    if not custom_symptoms or not custom_symptoms.strip():
        return None

    query_tokens = _tokenize(custom_symptoms)
    if not query_tokens:
        return None

    best: Optional[DiseaseKB] = None
    best_score = MATCH_MIN_SCORE  # acts as the threshold floor

    for disease in DiseaseKB.query.all():
        kb_tokens = _tokenize(disease.symptoms)
        overlap = query_tokens & kb_tokens
        if not overlap:
            continue
        # Recall: what fraction of the query words matched the KB entry?
        score = len(overlap) / len(query_tokens)
        if score > best_score:
            best_score = score
            best = disease

    return best


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------

def create_disease(
    name: str,
    symptoms: str,
    preventive_measures: str,
    incubation_period_days: Optional[int],
    added_by: int,
) -> DiseaseKB:
    """Create and flush a new DiseaseKB entry (caller must commit)."""
    entry = DiseaseKB(
        name=name,
        symptoms=symptoms,
        preventive_measures=preventive_measures,
        incubation_period_days=incubation_period_days,
        added_by=added_by,
    )
    db.session.add(entry)
    db.session.flush()
    return entry


def update_disease(disease: DiseaseKB, **fields) -> DiseaseKB:
    """Apply a partial update dict to an existing DiseaseKB row.
    Recognised keys: name, symptoms, preventive_measures, incubation_period_days.
    Caller must commit."""
    allowed = {"name", "symptoms", "preventive_measures", "incubation_period_days"}
    for key, value in fields.items():
        if key in allowed:
            setattr(disease, key, value)
    return disease
