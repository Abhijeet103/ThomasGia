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
        return JsonResponse(
            {
                "authenticated": True,
                "user": {
                    "email": request.user.email,
                    "role": request.user.role,
                    "is_paid_user": request.user.is_paid_user,
                    "subscription_expires_at": request.user.subscription_expires_at.isoformat() if request.user.subscription_expires_at else None,
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
