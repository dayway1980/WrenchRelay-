"""Descriptive pilot metrics from consented, human-reviewed cases; no causal claims."""
import argparse
import json
import math
from statistics import median


def summarize(cases):
    ids = set()
    deltas, helpful, abstentions = [], [], []
    for c in cases:
        identity = (c['tenant_id'], c['case_id'])
        if identity in ids:
            raise ValueError('Duplicate case')
        ids.add(identity)
        if c.get('authorized') is not True or c.get('human_reviewed') is not True:
            raise ValueError('Authorization and human review required')
        if c.get('dataset') not in ('synthetic', 'pilot'):
            raise ValueError('Dataset must be explicit')
        for name in ('helpful', 'abstained'):
            if type(c.get(name)) is not bool:
                raise ValueError('Explicit boolean review required')
        helpful.append(c['helpful'])
        abstentions.append(c['abstained'])
        pair = [c.get('baseline_minutes'), c.get('assisted_minutes')]
        if any(v is not None for v in pair):
            if not all(type(v) in (int, float) and math.isfinite(v) and v >= 0 for v in pair):
                raise ValueError('Timing requires two finite nonnegative observations')
            if not c.get('timing_protocol_id'):
                raise ValueError('Paired timings require protocol identification')
            deltas.append(pair[0] - pair[1])
    datasets = {c['dataset'] for c in cases}
    tenants = {c['tenant_id'] for c in cases}
    if len(datasets) > 1 or len(tenants) > 1:
        raise ValueError('Report one tenant and one dataset at a time')
    n = len(cases)
    return {
        'dataset': next(iter(datasets), None), 'reviewed_cases': n,
        'helpful_fraction': sum(helpful) / n if n else None,
        'abstention_fraction': sum(abstentions) / n if n else None,
        'paired_timing_cases': len(deltas),
        'median_observed_minutes_difference': median(deltas) if deltas else None,
        'limitations': 'Descriptive observations only; not causal time savings, MTTR, safety certification or calibrated confidence.',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', help='Authorized de-identified JSON array; do not commit pilot data')
    args = parser.parse_args()
    with open(args.input) as stream:
        print(json.dumps(summarize(json.load(stream)), indent=2, allow_nan=False))
