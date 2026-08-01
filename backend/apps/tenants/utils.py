from __future__ import annotations

from contextvars import ContextVar
from urllib.parse import urlparse

from django.conf import settings

from .models import Tenant


LOCAL_TENANT_HOSTS = {"127.0.0.1", "localhost", "testserver"}
_current_tenant_slug: ContextVar[str | None] = ContextVar("current_tenant_slug", default=None)


def normalize_host(host: str) -> str:
    host = (host or "").strip().lower()
    if not host:
        return ""
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def default_tenant_slug() -> str:
    return getattr(settings, "DEFAULT_TENANT_SLUG", "mindmetric")


def set_current_tenant_slug(slug: str | None):
    return _current_tenant_slug.set(slug)


def reset_current_tenant_slug(token) -> None:
    _current_tenant_slug.reset(token)


def get_current_tenant_slug() -> str:
    return _current_tenant_slug.get() or default_tenant_slug()


def get_current_tenant() -> Tenant | None:
    slug = get_current_tenant_slug()
    return Tenant.objects.filter(slug=slug, is_active=True).first()


def default_tenant_domain() -> str:
    parsed = urlparse(getattr(settings, "SITE_URL", "https://mindmetric.store"))
    return normalize_host(parsed.hostname or "mindmetric.store")


def get_default_tenant() -> Tenant | None:
    tenant = Tenant.objects.filter(slug=default_tenant_slug()).first()
    if tenant:
        return tenant
    return Tenant.objects.filter(is_active=True).order_by("id").first()


def resolve_tenant_from_host(host: str) -> Tenant | None:
    normalized = normalize_host(host)
    if not normalized:
        return get_default_tenant()

    base_domain = normalize_host(
        getattr(settings, "TENANT_BASE_DOMAIN", default_tenant_domain())
    )
    if normalized in {base_domain, f"www.{base_domain}"}:
        # The platform hostname is configuration-owned. Keep it available even
        # when an older database was seeded with a localhost or previous domain.
        return get_default_tenant()

    tenant = Tenant.objects.filter(is_active=True, primary_domain=normalized).first()
    if tenant:
        return tenant

    if normalized.startswith("www."):
        tenant = Tenant.objects.filter(is_active=True, primary_domain=normalized[4:]).first()
        if tenant:
            return tenant

    if normalized in LOCAL_TENANT_HOSTS:
        return get_default_tenant()

    return None
