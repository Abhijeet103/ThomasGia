from __future__ import annotations

import calendar
import json
import logging
from base64 import b64encode
from dataclasses import dataclass
from datetime import timedelta
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import stripe
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.models import User, UserRole
from backend.apps.accounts.emails import send_subscription_activated_email, send_subscription_canceled_email

from .models import Subscription, SubscriptionStatus


logger = logging.getLogger(__name__)


class BillingConfigurationError(Exception):
    pass


class BillingWebhookError(Exception):
    pass


@dataclass(frozen=True)
class PlanDefinition:
    code: str
    title: str
    price_display: str
    price_value: str
    duration_label: str
    summary: str
    price_id: str


PLAN_ORDER = ("weekly", "monthly", "yearly")


def _plan_rank(plan_code: str) -> int:
    try:
        return PLAN_ORDER.index(plan_code)
    except ValueError as exc:
        raise BillingConfigurationError(f"Unknown plan rank for code: {plan_code}") from exc


def _safe_plan_rank(plan_code: str | None) -> int | None:
    if not plan_code:
        return None
    try:
        return _plan_rank(plan_code)
    except BillingConfigurationError:
        logger.warning("Ignoring unknown subscription plan code while building billing UI: %s", plan_code)
        return None


def _price_id_for(plan_code: str) -> str:
    return {
        "weekly": settings.STRIPE_PRICE_WEEKLY,
        "monthly": settings.STRIPE_PRICE_MONTHLY,
        "yearly": settings.STRIPE_PRICE_YEARLY,
    }[plan_code]


def get_plan_catalog() -> list[PlanDefinition]:
    return [
        PlanDefinition(
            code="weekly",
            title="Weekly",
            price_display="$9.99",
            price_value="9.99",
            duration_label="7 days access",
            summary="Unlimited full tests and section-wise tests for one week.",
            price_id=_price_id_for("weekly"),
        ),
        PlanDefinition(
            code="monthly",
            title="Monthly",
            price_display="$19.99",
            price_value="19.99",
            duration_label="1 month access",
            summary="Unlimited full tests and section-wise tests for one month.",
            price_id=_price_id_for("monthly"),
        ),
        PlanDefinition(
            code="yearly",
            title="Yearly",
            price_display="$12.99",
            price_value="12.99",
            duration_label="1 year access",
            summary="Unlimited full tests and section-wise tests for one year.",
            price_id=_price_id_for("yearly"),
        ),
    ]


def get_plan_definition(plan_code: str) -> PlanDefinition:
    plans = {plan.code: plan for plan in get_plan_catalog()}
    try:
        return plans[plan_code]
    except KeyError as exc:
        raise BillingConfigurationError(f"Unknown plan code: {plan_code}") from exc


def stripe_is_configured() -> bool:
    return bool(
        settings.STRIPE_SECRET_KEY
        and settings.STRIPE_WEBHOOK_SECRET
        and settings.STRIPE_PRICE_WEEKLY
        and settings.STRIPE_PRICE_MONTHLY
        and settings.STRIPE_PRICE_YEARLY
    )


def paypal_is_configured() -> bool:
    return bool(settings.PAYPAL_CLIENT_ID and settings.PAYPAL_CLIENT_SECRET)


def paypal_webhook_is_configured() -> bool:
    return paypal_is_configured() and bool(settings.PAYPAL_WEBHOOK_ID)


def _paypal_api_base() -> str:
    if settings.PAYPAL_ENV == "live":
        return "https://api-m.paypal.com"
    return "https://api-m.sandbox.paypal.com"


def _paypal_basic_auth_header() -> str:
    credentials = f"{settings.PAYPAL_CLIENT_ID}:{settings.PAYPAL_CLIENT_SECRET}".encode("utf-8")
    return f"Basic {b64encode(credentials).decode('ascii')}"


def _paypal_access_token() -> str:
    if not paypal_is_configured():
        raise BillingConfigurationError("PayPal is not configured yet.")

    payload = "grant_type=client_credentials".encode("utf-8")
    request = Request(
        f"{_paypal_api_base()}/v1/oauth2/token",
        data=payload,
        method="POST",
        headers={
            "Authorization": _paypal_basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise BillingConfigurationError(f"PayPal token request failed: {detail or exc.reason}") from exc
    except URLError as exc:
        raise BillingConfigurationError(f"PayPal token request failed: {exc.reason}") from exc

    token = data.get("access_token")
    if not token:
        raise BillingConfigurationError("PayPal token response did not include an access token.")
    return token


def _paypal_request(method: str, path: str, payload: dict | None = None, *, access_token: str | None = None) -> dict:
    token = access_token or _paypal_access_token()
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{_paypal_api_base()}{path}",
        data=body,
        method=method.upper(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise BillingWebhookError(f"PayPal API request failed: {detail or exc.reason}") from exc
    except URLError as exc:
        raise BillingWebhookError(f"PayPal API request failed: {exc.reason}") from exc

    if not raw_body:
        return {}
    return json.loads(raw_body)


def _add_one_month(start):
    month = start.month + 1
    year = start.year
    if month > 12:
        month = 1
        year += 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return start.replace(year=year, month=month, day=day)


def _add_one_year(start):
    year = start.year + 1
    day = min(start.day, calendar.monthrange(year, start.month)[1])
    return start.replace(year=year, day=day)


def calculate_expiry(now, plan_code: str):
    if plan_code == "weekly":
        return now + timedelta(days=7)
    if plan_code == "monthly":
        return _add_one_month(now)
    if plan_code == "yearly":
        return _add_one_year(now)
    raise BillingConfigurationError(f"Unknown plan code for expiry calculation: {plan_code}")


def _build_absolute_url(path: str, base_url: str | None = None) -> str:
    return f"{(base_url or settings.SITE_URL).rstrip('/')}{path}"


def _subscription_base_time(user: User, now):
    if user.subscription_expires_at and user.subscription_expires_at > now:
        return user.subscription_expires_at
    return now


def _activate_subscription(
    *,
    user: User,
    plan_code: str,
    provider: str,
    provider_subscription_id: str,
    provider_customer_id: str = "",
    activated_at=None,
) -> Subscription:
    plan = get_plan_definition(plan_code)
    now = activated_at or timezone.now()
    subscription = Subscription.objects.filter(
        provider=provider,
        provider_subscription_id=provider_subscription_id,
    ).first()

    if subscription and subscription.status == SubscriptionStatus.ACTIVE and subscription.current_period_end and subscription.current_period_end > now:
        expiry = subscription.current_period_end
        created = False
        should_send_email = False
    else:
        expiry = calculate_expiry(_subscription_base_time(user, now), plan.code)
        created = subscription is None
        should_send_email = True

    user.subscriptions.filter(status__in=[SubscriptionStatus.PENDING, SubscriptionStatus.ACTIVE]).exclude(
        provider=provider,
        provider_subscription_id=provider_subscription_id,
    ).update(
        status=SubscriptionStatus.CANCELED,
        current_period_end=now,
    )

    subscription, _ = Subscription.objects.update_or_create(
        provider=provider,
        provider_subscription_id=provider_subscription_id,
        defaults={
            "user": user,
            "tenant": user.tenant,
            "plan_code": plan.code,
            "status": SubscriptionStatus.ACTIVE,
            "provider_customer_id": provider_customer_id,
            "current_period_start": now,
            "current_period_end": expiry,
        },
    )

    user.role = UserRole.PAID
    user.subscription_expires_at = expiry
    user.save(update_fields=["role", "subscription_expires_at"])
    if should_send_email:
        send_subscription_activated_email(user, plan.title, expiry)

    logger.info(
        "Activated %s subscription for user=%s plan=%s reference=%s created=%s expires_at=%s",
        provider,
        user.id,
        plan.code,
        provider_subscription_id,
        created,
        expiry.isoformat(),
    )
    return subscription


def _paypal_custom_id(user: User, plan_code: str) -> str:
    return json.dumps(
        {
            "user_id": user.id,
            "plan_code": plan_code,
            "tenant_id": user.tenant_id or "",
        },
        separators=(",", ":"),
    )


def _parse_paypal_custom_id(value: str | None) -> dict[str, str]:
    if not value:
        raise BillingWebhookError("PayPal purchase unit metadata is missing.")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise BillingWebhookError("PayPal purchase unit metadata is invalid.") from exc
    if not parsed.get("user_id") or not parsed.get("plan_code"):
        raise BillingWebhookError("PayPal purchase unit metadata is incomplete.")
    return parsed


def build_plan_cards(user: User | None, active_subscription: Subscription | None) -> list[dict[str, object]]:
    current_plan_code = active_subscription.plan_code if active_subscription else None
    has_active_subscription = bool(active_subscription and active_subscription.status == SubscriptionStatus.ACTIVE)
    current_plan_rank = _safe_plan_rank(current_plan_code)
    cards: list[dict[str, object]] = []
    for plan in get_plan_catalog():
        is_current = plan.code == current_plan_code
        plan_rank = _plan_rank(plan.code)
        show_action = True
        if not user or not user.is_authenticated:
            button_label = "Sign in to buy"
        elif is_current:
            button_label = "Current plan"
        elif has_active_subscription:
            if current_plan_rank is not None and plan_rank > current_plan_rank:
                button_label = "Upgrade"
            else:
                button_label = ""
                show_action = False
        else:
            button_label = "Buy now"
        cards.append(
            {
                "code": plan.code,
                "title": plan.title,
                "price_display": plan.price_display,
                "duration_label": plan.duration_label,
                "summary": plan.summary,
                "is_current": is_current,
                "button_label": button_label,
                "is_disabled": is_current,
                "show_action": show_action,
                "paypal_button_label": f"{button_label} with PayPal" if button_label else "",
                "stripe_button_label": f"{button_label} with card" if button_label else "",
            }
        )
    return cards


def create_checkout_session(user: User, plan_code: str, base_url: str | None = None) -> str:
    if not user.is_authenticated:
        raise BillingConfigurationError("Authentication required to start checkout.")
    if not stripe_is_configured():
        raise BillingConfigurationError("Stripe is not configured yet.")

    plan = get_plan_definition(plan_code)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = _build_absolute_url(f"{reverse('pages:subscription')}?checkout=processing", base_url=base_url)
    cancel_url = _build_absolute_url(f"{reverse('pages:subscription')}?checkout=cancelled", base_url=base_url)

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": plan.price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(user.id),
        customer_email=user.email,
        metadata={"user_id": str(user.id), "plan_code": plan.code, "tenant_id": str(user.tenant_id or "")},
        payment_intent_data={"metadata": {"user_id": str(user.id), "plan_code": plan.code, "tenant_id": str(user.tenant_id or "")}},
    )

    logger.info(
        "Created Stripe checkout session for user=%s plan=%s session=%s",
        user.id,
        plan.code,
        checkout_session.id,
    )
    return checkout_session.url


def create_paypal_order(user: User, plan_code: str, base_url: str | None = None) -> str:
    if not user.is_authenticated:
        raise BillingConfigurationError("Authentication required to start checkout.")
    if not paypal_is_configured():
        raise BillingConfigurationError("PayPal is not configured yet.")

    plan = get_plan_definition(plan_code)
    return_url = _build_absolute_url(reverse("billing-paypal-return"), base_url=base_url)
    cancel_url = _build_absolute_url(f"{reverse('pages:subscription')}?checkout=cancelled", base_url=base_url)

    order_payload = _paypal_request(
        "POST",
        "/v2/checkout/orders",
        {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "amount": {
                        "currency_code": "USD",
                        "value": plan.price_value,
                    },
                    "description": f"MindMetric {plan.title} access",
                    "custom_id": _paypal_custom_id(user, plan.code),
                }
            ],
            "payment_source": {
                "paypal": {
                    "experience_context": {
                        "return_url": return_url,
                        "cancel_url": cancel_url,
                        "brand_name": settings.PAYPAL_BRAND_NAME,
                        "shipping_preference": "NO_SHIPPING",
                        "user_action": "PAY_NOW",
                    }
                }
            },
        },
    )

    order_id = order_payload.get("id", "")
    if order_id:
        Subscription.objects.update_or_create(
            provider="paypal",
            provider_subscription_id=order_id,
            defaults={
                "user": user,
                "tenant": user.tenant,
                "plan_code": plan.code,
                "status": SubscriptionStatus.PENDING,
                "provider_customer_id": "",
                "current_period_start": timezone.now(),
                "current_period_end": None,
            },
        )

    for link in order_payload.get("links", []):
        if link.get("rel") in {"payer-action", "approve"} and link.get("href"):
            logger.info("Created PayPal order for user=%s plan=%s order=%s", user.id, plan.code, order_id)
            return link["href"]
    raise BillingWebhookError("PayPal did not return an approval URL for the order.")


def get_paypal_order(order_id: str) -> dict:
    if not order_id:
        raise BillingWebhookError("Missing PayPal order id.")
    return _paypal_request("GET", f"/v2/checkout/orders/{order_id}")


def capture_paypal_order(order_id: str) -> dict:
    if not order_id:
        raise BillingWebhookError("Missing PayPal order id.")
    return _paypal_request("POST", f"/v2/checkout/orders/{order_id}/capture", {})


def sync_user_subscription_access(user: User) -> User:
    if not user.is_authenticated:
        return user

    active_subscription = (
        user.subscriptions.filter(status=SubscriptionStatus.ACTIVE)
        .order_by("-current_period_end", "-updated_at")
        .first()
    )
    now = timezone.now()
    updates: list[str] = []

    if active_subscription and active_subscription.current_period_end:
        if active_subscription.current_period_end > now:
            if user.role != UserRole.PAID:
                user.role = UserRole.PAID
                updates.append("role")
            if user.subscription_expires_at != active_subscription.current_period_end:
                user.subscription_expires_at = active_subscription.current_period_end
                updates.append("subscription_expires_at")
        else:
            if active_subscription.status != SubscriptionStatus.EXPIRED:
                active_subscription.status = SubscriptionStatus.EXPIRED
                active_subscription.save(update_fields=["status", "updated_at"])

    if user.subscription_expires_at and user.subscription_expires_at <= now:
        if user.role != UserRole.FREE:
            user.role = UserRole.FREE
            updates.append("role")
        if user.subscription_expires_at is not None:
            user.subscription_expires_at = None
            updates.append("subscription_expires_at")

    if not active_subscription and user.role == UserRole.PAID and not user.has_active_subscription:
        user.role = UserRole.FREE
        updates.append("role")

    if updates:
        user.save(update_fields=list(dict.fromkeys(updates)))
    return user


def activate_subscription_from_checkout(session_payload: dict) -> Subscription:
    metadata = session_payload.get("metadata") or {}
    user_id = metadata.get("user_id")
    plan_code = metadata.get("plan_code")
    if not user_id or not plan_code:
        raise BillingWebhookError("Stripe session metadata is missing user_id or plan_code.")

    try:
        user = User.objects.get(pk=int(user_id))
    except User.DoesNotExist as exc:
        raise BillingWebhookError(f"User {user_id} not found for Stripe checkout session.") from exc

    return _activate_subscription(
        user=user,
        plan_code=plan_code,
        provider="stripe",
        provider_subscription_id=session_payload["id"],
        provider_customer_id=session_payload.get("customer") or "",
    )


def activate_subscription_from_paypal_order(order_payload: dict) -> Subscription:
    purchase_units = order_payload.get("purchase_units") or []
    if not purchase_units:
        raise BillingWebhookError("PayPal order payload is missing purchase units.")

    metadata = _parse_paypal_custom_id(purchase_units[0].get("custom_id"))
    try:
        user = User.objects.get(pk=int(metadata["user_id"]))
    except User.DoesNotExist as exc:
        raise BillingWebhookError(f"User {metadata['user_id']} not found for PayPal order.") from exc

    payer = order_payload.get("payer") or {}
    provider_customer_id = payer.get("payer_id", "")
    provider_subscription_id = order_payload.get("id", "")
    if not provider_subscription_id:
        raise BillingWebhookError("PayPal order payload is missing an order id.")

    return _activate_subscription(
        user=user,
        plan_code=metadata["plan_code"],
        provider="paypal",
        provider_subscription_id=provider_subscription_id,
        provider_customer_id=provider_customer_id,
    )


def construct_stripe_event(payload: bytes, signature: str):
    if not stripe_is_configured():
        raise BillingConfigurationError("Stripe is not configured yet.")

    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        return stripe.Webhook.construct_event(payload=payload, sig_header=signature, secret=settings.STRIPE_WEBHOOK_SECRET)
    except ValueError as exc:
        raise BillingWebhookError("Invalid Stripe webhook payload.") from exc
    except stripe.error.SignatureVerificationError as exc:
        raise BillingWebhookError("Invalid Stripe webhook signature.") from exc


def verify_paypal_webhook(*, headers: dict[str, str], event_payload: dict) -> bool:
    if not paypal_webhook_is_configured():
        raise BillingConfigurationError("PayPal webhook verification is not configured yet.")

    verification = _paypal_request(
        "POST",
        "/v1/notifications/verify-webhook-signature",
        {
            "auth_algo": headers.get("PAYPAL-AUTH-ALGO", ""),
            "cert_url": headers.get("PAYPAL-CERT-URL", ""),
            "transmission_id": headers.get("PAYPAL-TRANSMISSION-ID", ""),
            "transmission_sig": headers.get("PAYPAL-TRANSMISSION-SIG", ""),
            "transmission_time": headers.get("PAYPAL-TRANSMISSION-TIME", ""),
            "webhook_id": settings.PAYPAL_WEBHOOK_ID,
            "webhook_event": event_payload,
        },
    )
    return verification.get("verification_status") == "SUCCESS"


def cancel_user_subscription(user: User) -> User:
    now = timezone.now()
    user.subscriptions.filter(status=SubscriptionStatus.ACTIVE).update(
        status=SubscriptionStatus.CANCELED,
        current_period_end=now,
    )
    user.role = UserRole.FREE
    user.subscription_expires_at = None
    user.save(update_fields=["role", "subscription_expires_at"])
    send_subscription_canceled_email(user)
    logger.info("Canceled subscription access for user=%s", user.id)
    return user
