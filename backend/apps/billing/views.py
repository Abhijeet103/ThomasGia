from __future__ import annotations

import json

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
    activate_subscription_from_paypal_order,
    cancel_user_subscription,
    capture_paypal_order,
    construct_stripe_event,
    create_checkout_session,
    create_paypal_order,
    get_paypal_order,
    paypal_webhook_is_configured,
    sync_user_subscription_access,
    verify_paypal_webhook,
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
            checkout_url = create_checkout_session(request.user, plan_code, base_url=f"{request.scheme}://{request.get_host()}")
        except BillingConfigurationError as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")

        return redirect(checkout_url)


class StartPayPalCheckoutView(View):
    def post(self, request, plan_code: str):
        if not request.user.is_authenticated:
            return redirect(f"/login/?next={request.path}")

        try:
            approval_url = create_paypal_order(request.user, plan_code, base_url=f"{request.scheme}://{request.get_host()}")
        except (BillingConfigurationError, BillingWebhookError) as exc:
            messages.error(request, str(exc))
            return redirect(request.META.get("HTTP_REFERER") or "pages:subscription")

        return redirect(approval_url)


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


class PayPalReturnView(View):
    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("pages:login")

        order_id = request.GET.get("token", "").strip()
        if not order_id:
            messages.error(request, "PayPal did not return an order token.")
            return redirect("pages:subscription")

        try:
            capture_payload = capture_paypal_order(order_id)
            activate_subscription_from_paypal_order(capture_payload)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            messages.error(request, str(exc))
            return redirect(f"{request.build_absolute_uri('/subscription/')}?checkout=cancelled")

        messages.success(request, "PayPal payment confirmed. Your access is now active.")
        return redirect("pages:subscription")


@method_decorator(csrf_exempt, name="dispatch")
class PayPalWebhookView(View):
    def post(self, request):
        if not paypal_webhook_is_configured():
            return HttpResponseBadRequest("PayPal webhook verification is not configured yet.")

        try:
            event_payload = json.loads(request.body.decode("utf-8"))
        except json.JSONDecodeError:
            return HttpResponseBadRequest("Invalid PayPal webhook payload.")

        try:
            verified = verify_paypal_webhook(headers=request.headers, event_payload=event_payload)
        except (BillingConfigurationError, BillingWebhookError) as exc:
            return HttpResponseBadRequest(str(exc))

        if not verified:
            return HttpResponseBadRequest("Invalid PayPal webhook signature.")

        event_type = event_payload.get("event_type", "")
        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            order_id = (
                (((event_payload.get("resource") or {}).get("supplementary_data") or {}).get("related_ids") or {}).get("order_id", "")
            )
            if order_id:
                try:
                    order_payload = get_paypal_order(order_id)
                    activate_subscription_from_paypal_order(order_payload)
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
