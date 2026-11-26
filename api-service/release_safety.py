"""Fail-closed defaults for deployments that must never access live customer systems.

The Vercel project currently has secrets with BOTH production and preview targets.
A preview is not an isolated environment just because its hostname differs.
This safeguard intentionally makes an unisolated preview read-only/degraded.

An operator must provision a genuinely isolated database and test API project
before setting WRENCHRELAY_PREVIEW_ISOLATED_BACKEND=true.
"""
import os


def unisolated_preview(env=None) -> bool:
    variables = os.environ if env is None else env
    return (
        variables.get("VERCEL_ENV", "").strip().lower() == "preview"
        and variables.get("WRENCHRELAY_PREVIEW_ISOLATED_BACKEND", "").strip().lower() != "true"
    )


def allow_external_services(env=None) -> bool:
    """Never authorize database, AI, or billing actions on an unisolated preview."""
    return not unisolated_preview(env)
