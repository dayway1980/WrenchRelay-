"""Assess supplied deployment evidence offline; never deploy or approve a release.

Evidence must be collected and reviewed independently. This checks consistency
and completeness, not authenticity. No credentials or network access are used.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re


PROJECTS = ('wrench-relay', 'wrenchrelay-industrial')
CHECKS = ('source-checks', 'container-build')
PROOFS = ('source_parity', 'storage_compatibility', 'session_compatibility',
          'backup_restore', 'customer_workflows', 'payment_safeguards', 'rollback')
MAX_AGE_SECONDS = 4 * 60 * 60


def record(value):
    return value if isinstance(value, dict) else {}


def records(value):
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def fresh(stamp, now):
    if not isinstance(stamp, str):
        return False
    try:
        observed = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
        if observed.utcoffset() is None:
            return False
        age = (now - observed).total_seconds()
        return -300 <= age <= MAX_AGE_SECONDS
    except (ValueError, OverflowError):
        return False


def evaluate(snapshot, expected_commit, target, *, now=None):
    """Return technical blockers for one explicit target and exact candidate SHA."""
    if not isinstance(snapshot, dict):
        raise ValueError('Evidence must be an object')
    if not isinstance(expected_commit, str) or not re.fullmatch('[0-9a-f]{40}', expected_commit):
        raise ValueError('A full lowercase commit SHA is required')
    if target not in ('vercel', 'cloudflare'):
        raise ValueError('An explicit supported target is required')
    now = now or datetime.now(timezone.utc)
    if now.utcoffset() is None:
        raise ValueError('An aware evaluation time is required')
    blockers = []

    def require(condition, label):
        if not condition and label not in blockers:
            blockers.append(label)

    def verified(item, label):
        item = record(item)
        source = item.get('source')
        valid = (item.get('commit') == expected_commit
                 and isinstance(source, str) and bool(source.strip())
                 and fresh(item.get('observed_at'), now))
        require(valid, label + ':evidence')
        return valid

    def ready(item, label):
        item = record(item)
        verified(item, label)
        require(type(item.get('http_status')) is int and item.get('http_status') == 200
                and item.get('database') == 'ok', label)

    require(type(snapshot.get('schema_version')) is int and snapshot.get('schema_version') == 1,
            'snapshot:schema_version')
    require(snapshot.get('candidate_commit') == expected_commit, 'snapshot:commit')
    require(fresh(snapshot.get('observed_at'), now), 'snapshot:freshness')

    github = record(snapshot.get('github'))
    verified(github, 'github')
    checks = records(github.get('checks'))
    for name in CHECKS:
        matches = [item for item in checks if item.get('name') == name]
        require(len(matches) == 1 and matches[0].get('status') == 'completed'
                and matches[0].get('conclusion') == 'success', 'github:' + name)

    deployments = records(snapshot.get('vercel'))
    paths = {'vercel': {}, 'cloudflare': 'unknown'}
    for project in PROJECTS:
        matches = [item for item in deployments if item.get('project') == project]
        item = matches[0] if len(matches) == 1 else {}
        build_ready = (item.get('commit') == expected_commit and item.get('state') == 'READY'
                       and item.get('environment') == 'preview')
        paths['vercel'][project] = 'BUILD_READY' if build_ready else 'UNVERIFIED'
        if target == 'vercel':
            label = 'vercel:' + project
            require(len(matches) == 1, label + ':missing_or_duplicate')
            verified(item, label)
            require(build_ready, label + ':build')
            ready(item.get('readiness'), label + ':readiness')

    cloudflare = record(snapshot.get('cloudflare'))
    cf_state = cloudflare.get('state')
    if cloudflare.get('commit') == expected_commit and cf_state in ('success', 'failed', 'in_progress'):
        paths['cloudflare'] = cf_state
    if target == 'cloudflare':
        verified(cloudflare, 'cloudflare')
        require(cloudflare.get('scope') == 'non-production-version-upload', 'cloudflare:scope')
        require(cloudflare.get('state') == 'success', 'cloudflare:build')
        ready(cloudflare.get('readiness'), 'cloudflare:readiness')

    proofs = record(snapshot.get('proofs'))
    for name in PROOFS:
        proof = record(proofs.get(name))
        verified(proof, 'proof:' + name)
        require(proof.get('result') == 'passed', 'proof:' + name)

    return {'decision': 'BLOCKED' if blockers else 'TECHNICAL_CHECKS_PASSED',
            'candidate_commit': expected_commit, 'target': target,
            'production_approved': False, 'paths': paths, 'blockers': blockers,
            'assessed_at': now.astimezone(timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path, help='Sanitized, independently reviewed JSON evidence')
    parser.add_argument('--commit', required=True, help='Full candidate commit SHA')
    parser.add_argument('--target', choices=('vercel', 'cloudflare'), required=True)
    args = parser.parse_args()
    try:
        snapshot = json.loads(args.evidence.read_text(encoding='utf-8'))
        result = evaluate(snapshot, args.commit, args.target)
    except (OSError, UnicodeError, ValueError):
        # Do not echo file contents, paths, credentials, or parser excerpts.
        print(json.dumps({'decision': 'INVALID_EVIDENCE', 'production_approved': False}))
        return 3
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result['blockers'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
