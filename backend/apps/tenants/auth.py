from __future__ import annotations


SESSION_TENANT_KEY = "_mindmetric_auth_tenant_id"


def bind_session_to_tenant(request, tenant=None) -> None:
    tenant = tenant or getattr(request, "tenant", None)
    if tenant is None:
        return
    request.session[SESSION_TENANT_KEY] = tenant.pk


def session_tenant_id(request) -> int | None:
    value = request.session.get(SESSION_TENANT_KEY)
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None
