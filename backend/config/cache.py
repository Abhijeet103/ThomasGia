from __future__ import annotations

from backend.apps.tenants.utils import get_current_tenant_slug


def tenant_cache_key(key: str, key_prefix: str, version: int) -> str:
    tenant_slug = get_current_tenant_slug()
    return f"{key_prefix}:{tenant_slug}:{version}:{key}"
