from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import logout
from django.conf import settings
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.utils import timezone

from .models import TenantUser, TenantUserStatus
from .services import get_or_create_tenant_user, get_tenant_access, is_institution_tenant
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


class TenantUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant_user = None
        user = getattr(request, "user", None)
        tenant = getattr(request, "tenant", None)
        if tenant is not None and user is not None and user.is_authenticated:
            request.tenant_user = get_or_create_tenant_user(tenant=tenant, user=user)
            now = timezone.now()
            if (
                request.tenant_user
                and (
                    request.tenant_user.last_seen_at is None
                    or request.tenant_user.last_seen_at < now - timedelta(minutes=15)
                )
            ):
                TenantUser.objects.filter(pk=request.tenant_user.pk).update(last_seen_at=now)
                request.tenant_user.last_seen_at = now
            if (
                request.tenant_user
                and request.tenant_user.status == TenantUserStatus.SUSPENDED
                and request.path != "/accounts/logout/"
            ):
                return HttpResponseForbidden("Your access to this tenant has been suspended.")
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
            request.session["tenant_oauth_tenant_id"] = tenant.id
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

    @staticmethod
    def _set_platform_access(request, user):
        is_authenticated = bool(user is not None and user.is_authenticated)
        is_active = bool(is_authenticated and user.has_active_subscription)
        request.effective_role = "paid" if is_active else ("free" if is_authenticated else "guest")
        request.effective_role_label = user.get_role_display() if is_authenticated else "Guest"
        request.effective_plan_code = None
        request.effective_access_expires_at = (
            user.subscription_expires_at if is_active else None
        )
        request.effective_access_active = is_active
        request.effective_access_source = "platform"
        request.effective_access_source_label = "MindMetric"
        request.effective_access_tenant_managed = False

    @staticmethod
    def _set_tenant_access(request, tenant, membership):
        if membership is None or not membership.is_active:
            return
        request.effective_role = "paid"
        request.effective_role_label = f"{membership.get_plan_code_display()} plan"
        request.effective_plan_code = membership.plan_code
        request.effective_access_expires_at = membership.access_expires_at
        request.effective_access_active = True
        request.effective_access_source = "tenant"
        request.effective_access_source_label = tenant.name
        request.effective_access_tenant_managed = True

    def __call__(self, request):
        tenant = getattr(request, "tenant", None)
        user = getattr(request, "user", None)
        request.tenant_membership = None
        self._set_platform_access(request, user)
        if (
            is_institution_tenant(tenant)
            and user is not None
            and user.is_authenticated
        ):
            access = get_tenant_access(tenant=tenant, user=user)
            request.tenant_membership = access.membership
            request.tenant_user = access.tenant_user
            self._set_tenant_access(request, tenant, access.membership)
            if (
                not access.allowed
                and not request.path.startswith(self.EXEMPT_PREFIXES)
            ):
                activation_url = reverse("tenants:activate")
                return redirect(f"{activation_url}?next={request.get_full_path()}")
        return self.get_response(request)
