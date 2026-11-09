"""Fail-closed validation of browser redirect URLs for Stripe-hosted flows.

Allowed origins come from server configuration, never from request data.
"""

from urllib.parse import urlsplit


def _parts(value: str):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError("Invalid redirect URL")
    # urlsplit removes some control characters; reject them before parsing.
    if any(ord(char) < 33 or ord(char) == 127 for char in value) or "\\" in value:
        raise ValueError("Invalid redirect URL")
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        port = parsed.port  # Force validation of malformed ports.
    except ValueError as exc:
        raise ValueError("Invalid redirect URL") from exc
    if (
        parsed.scheme not in {"https", "http"}
        or not parsed.netloc
        or not host
        or host.endswith(".")
        or parsed.username is not None
        or parsed.password is not None
        or port == 0
        or parsed.fragment
    ):
        raise ValueError("Invalid redirect URL")
    if parsed.scheme == "http" and host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("HTTPS is required for public redirects")
    return parsed


def _origin(value: str, *, configured: bool = False) -> tuple[str, str, int]:
    parsed = _parts(value)
    if configured and (parsed.path not in {"", "/"} or parsed.query):
        raise ValueError("Configured frontend URL must be an origin")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return parsed.scheme, parsed.hostname, port


def approved_redirect(value: str, configured_origins: list[str], *, origin_only: bool = False) -> str:
    """Return validated URL; raise ValueError for unsafe or unconfigured URLs.

    Rejects prefix-lookalike hosts, insecure remote HTTP, userinfo, fragments,
    protocol-relative URLs, backslashes, embedded controls and malformed ports.
    """
    candidate = _parts(value)
    if origin_only and (candidate.path not in {"", "/"} or candidate.query):
        raise ValueError("A frontend origin is required")
    allowed = set()
    for configured in configured_origins:
        if configured:
            allowed.add(_origin(configured.strip(), configured=True))
    if not allowed or _origin(value) not in allowed:
        raise ValueError("Redirect origin is not approved")
    return value.rstrip("/") if origin_only else value
