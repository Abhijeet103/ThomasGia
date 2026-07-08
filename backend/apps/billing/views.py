from __future__ import annotations

from django.contrib import messages
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from .services import (
    BillingConfigurationError,
    BillingWebhookError,
    activate_subscription_from_checkout,
    cancel_user_subscription,
    construct_stripe_event,
    create_checkout_session,
    sync_user_subscription_access,
)


class BillingStatusView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)

        sync_user_subscription_access(request.user)
        active = request.user.subscriptions.filter(status="active").first()
        return JsonResponse(
            {
                "role": request.user.role,
                "subscription_expires_at": request.user.subscription_expires_at.isoformat() if request.user.subscription_expires_at else None,
                "subscription": {
                    "active": bool(active),
                    "plan_code": active.plan_code if active else None,
                },
            }
        )


class StartCheckoutView(View):
    def post(self, request, plan_code: str):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")

        try:
            checkout_url = create_checkout_session(request.user, plan_code)
        except BillingConfigurationError as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")

        return redirect(checkout_url)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request):
        signature = request.META.get("HTTP_STRIPE_SIGNATURE", "")
        try:
            event = construct_stripe_event(request.body, signature)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        event_type = event["type"]
        if event_type in {"checkout.session.completed", "checkout.session.async_payment_succeeded"}:
            session_payload = event["data"]["object"]
            if session_payload.get("payment_status") == "paid":
                try:
                    activate_subscription_from_checkout(session_payload)
                except (BillingConfigurationError, BillingWebhookError) as exc:
                    return HttpResponseBadRequest(str(exc))

        return JsonResponse({"received": True, "type": event_type})


class CancelSubscriptionView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("pages:login")

        cancel_user_subscription(request.user)
        messages.success(request, "Your subscription has been canceled.")
        return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")
