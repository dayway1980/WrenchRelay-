"""Evidence admissibility checks; no generated diagnoses or calibrated probabilities."""
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class Fact:
    id: str
    tenant: str
    asset: str
    value: str
    source_record: str
    source_field: str
    source_revision: str
    observed_at: datetime
    retrieved_at: datetime


def admissible(fact: Fact, *, tenant: str, asset: str, now: datetime, max_age: timedelta) -> bool:
    if not all(isinstance(v, str) and v.strip() for v in
               (fact.id, fact.tenant, fact.asset, fact.value, fact.source_record,
                fact.source_field, fact.source_revision)):
        return False
    times = (fact.observed_at, fact.retrieved_at, now)
    if any(t.tzinfo is None or t.utcoffset() is None for t in times):
        return False
    return (fact.tenant == tenant and fact.asset == asset and max_age.total_seconds() > 0
            and fact.observed_at <= fact.retrieved_at <= now
            and now - fact.observed_at <= max_age)


def assess(facts, *, tenant, asset, now, max_age, supporting_ids, contradicting_ids=()):
    """Judge supplied evidence links, not a diagnostic probability.

    Human-authored or separately reviewed hypotheses supply these links. This
    function does not infer that a fact actually supports a mechanical cause.
    """
    ids = [f.id for f in facts]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate evidence IDs')
    support, contradict = set(supporting_ids), set(contradicting_ids)
    valid = {f.id for f in facts if admissible(f, tenant=tenant, asset=asset, now=now, max_age=max_age)}
    missing = (support | contradict) - valid
    abstain = bool(missing or not support or contradict or support & contradict)
    return {'diagnosis': 'UNRESOLVED', 'abstain': abstain,
            'evidence_strength': 'insufficient_or_conflicting' if abstain else 'supporting_evidence_requires_human_review',
            'supporting_ids': sorted(support & valid), 'contradicting_ids': sorted(contradict & valid),
            'invalid_or_missing_ids': sorted(missing), 'probability': None}
