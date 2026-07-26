from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View

from .services import get_tenant_access, is_institution_tenant, redeem_enrollment_code
from .models import EnrollmentMode


class TenantAccessActivationView(LoginRequiredMixin, View):
    login_url = "/login/"
    template_name = "tenants/activate_access.html"

    def dispatch(self, request, *args, **kwargs):
        tenant = getattr(request, "tenant", None)
        if not is_institution_tenant(tenant):
            return redirect("pages:home")
        access = get_tenant_access(tenant=tenant, user=request.user)
        if access.allowed:
            return redirect(self._next_url(request))
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, self._context(request))

    def post(self, request):
        if request.tenant.enrollment_mode != EnrollmentMode.CODE_REQUIRED:
            messages.error(request, "Your institution administrator must renew this access.")
            return render(request, self.template_name, self._context(request), status=403)
        raw_code = request.POST.get("enrollment_code", "")
        membership = redeem_enrollment_code(
            tenant=request.tenant,
            user=request.user,
            raw_code=raw_code,
        )
        if membership is None:
            messages.error(request, "That enrollment code is invalid, expired, or has reached its usage limit.")
            return render(request, self.template_name, self._context(request), status=400)
        messages.success(request, f"Access to {request.tenant.name} is now active.")
        return redirect(self._next_url(request))

    def _next_url(self, request):
        next_url = request.POST.get("next") or request.GET.get("next") or reverse("pages:practice")
        if url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return next_url
        return reverse("pages:practice")

    def _context(self, request):
        return {
            "page_title": f"Activate access | {request.tenant.name}",
            "meta_robots": "noindex,nofollow",
            "tenant": request.tenant,
            "requires_code": request.tenant.enrollment_mode == EnrollmentMode.CODE_REQUIRED,
            "next": self._next_url(request),
        }
