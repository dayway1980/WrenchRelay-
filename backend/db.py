"""Database connection pool and session helpers.

Uses Supabase (Postgres) via the supabase-py client. The SUPABASE_URL
and SUPABASE_SERVICE_ROLE_KEY environment variables are required.
"""

import os
from functools import lru_cache

from supabase import create_client, Client


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    """Return a cached Supabase client instance."""
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return create_client(url, key)


def get_db() -> Client:
    """FastAPI dependency — yields the Supabase client."""
    return get_supabase()


# Future: connection-pool health check
# Future: read-replica routing
# Future: migration runner integration
# Future: query logging / slow-query alerts
# Future: per-tenant connection isolation
# Future: automatic reconnect on transient failures
# Future: metrics export (pool size, wait time)
# Future: schema version assertion at startup
