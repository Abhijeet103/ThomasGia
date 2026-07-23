from __future__ import annotations

from urllib.parse import urlparse

from django.conf import settings

from .models import Tenant


LOCAL_TENANT_HOSTS = {"127.0.0.1", "localhost", "testserver"}


def normalize_host(host: str) -> str:
    host = (host or "").strip().lower()
    if not host:
        return ""
    if ":" in host:
        host = host.split(":", 1)[0]
    return host


def default_tenant_slug() -> str:
    return getattr(settings, "DEFAULT_TENANT_SLUG", "mindmetric")


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

