from __future__ import annotations

from django.conf import settings
from django.http import JsonResponse
from django.views import View

from backend.apps.billing.services import sync_user_subscription_access


class SessionView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse(
                {
                    "authenticated": False,
                    "login_url": f"{request.scheme}://{request.get_host()}/accounts/google/login/",
                    "default_role": "free",
                },
                status=401,
            )

        sync_user_subscription_access(request.user)
        expires_at = request.effective_access_expires_at
        return JsonResponse(
            {
                "authenticated": True,
                "user": {
                    "email": request.user.email,
                    "role": request.effective_role,
                    "role_label": request.effective_role_label,
                    "is_paid_user": request.effective_access_active,
                    "subscription_expires_at": expires_at.isoformat() if expires_at else None,
                    "plan_code": request.effective_plan_code,
                    "access_source": request.effective_access_source,
                    "access_source_label": request.effective_access_source_label,
                    "tenant_managed": request.effective_access_tenant_managed,
                },
            }
        )


class GoogleOAuthConfigView(View):
    def get(self, request):
        return JsonResponse(
                {
                    "provider": "google",
                    "default_role": "free",
                    "login_url": f"{request.scheme}://{request.get_host()}/accounts/google/login/",
                    "site_url": settings.SITE_URL,
                    "upgrade_rule": "Users start as free and become paid after a successful purchase.",
                }
        )
