from __future__ import annotations

from django.contrib.auth import logout
from django.http import HttpResponseForbidden

from .utils import reset_current_tenant_slug, resolve_tenant_from_host, set_current_tenant_slug


class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = resolve_tenant_from_host(request.get_host())
        token = set_current_tenant_slug(getattr(request.tenant, "slug", None))
        try:
            return self.get_response(request)
        finally:
            reset_current_tenant_slug(token)


class TenantAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None)
        if (
            tenant is not None
            and user is not None
            and user.is_authenticated
            and not user.is_superuser
            and getattr(user, "tenant_id", None)
            and user.tenant_id != tenant.id
        ):
            logout(request)
            return HttpResponseForbidden("This account does not belong to this tenant.")
        return self.get_response(request)
