from __future__ import annotations

from django.contrib.auth import logout
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from .services import get_tenant_access, is_institution_tenant
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
            and user.is_tenant_admin
            and getattr(user, "tenant_id", None)
            and user.tenant_id != tenant.id
        ):
            logout(request)
            return HttpResponseForbidden("This account does not belong to this tenant.")
        return self.get_response(request)


class TenantOAuthHandoffMiddleware:
    GOOGLE_LOGIN_PATH = "/accounts/google/login/"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        if (
            is_institution_tenant(tenant)
            and request.method == "GET"
            and request.path == self.GOOGLE_LOGIN_PATH
        ):
            return_path = request.GET.get("next") or "/practice/"
            if not return_path.startswith("/"):
                return_path = "/practice/"
            request.session["tenant_oauth_return_url"] = (
                f"{request.scheme}://{request.get_host()}{return_path}"
            )
            apex_url = f"{settings.SITE_URL.rstrip('/')}{self.GOOGLE_LOGIN_PATH}"
            return redirect(apex_url)
        return self.get_response(request)


class TenantEnrollmentMiddleware:
    EXEMPT_PREFIXES = (
        "/admin/",
        "/accounts/",
        "/api/auth/",
        "/static/",
        "/robots.txt",
        "/sitemap.xml",
        "/tenant-access/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        user = getattr(request, "user", None)
        if (
            is_institution_tenant(tenant)
            and user is not None
            and user.is_authenticated
            and not request.path.startswith(self.EXEMPT_PREFIXES)
        ):
            access = get_tenant_access(tenant=tenant, user=user)
            request.tenant_membership = access.membership
            if not access.allowed:
                activation_url = reverse("tenants:activate")
                return redirect(f"{activation_url}?next={request.get_full_path()}")
        return self.get_response(request)
