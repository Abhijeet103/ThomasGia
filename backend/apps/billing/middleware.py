from __future__ import annotations

from .services import sync_user_subscription_access


class SubscriptionAccessMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) is not None and request.user.is_authenticated:
            sync_user_subscription_access(request.user)
        return self.get_response(request)
