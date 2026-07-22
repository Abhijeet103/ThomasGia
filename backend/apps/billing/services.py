from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import timedelta

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
            price_display="$4.99",
            duration_label="7 days access",
            summary="Unlimited full tests and section-wise tests for one week.",
            price_id=_price_id_for("weekly"),
        ),
        PlanDefinition(
            code="monthly",
            title="Monthly",
            price_display="$9.99",
            duration_label="1 month access",
            summary="Unlimited full tests and section-wise tests for one month.",
            price_id=_price_id_for("monthly"),
        ),
        PlanDefinition(
            code="yearly",
            title="Yearly",
            price_display="$12.99",
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


def _build_absolute_url(path: str) -> str:
    return f"{settings.SITE_URL.rstrip('/')}{path}"


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
            }
        )
    return cards


def create_checkout_session(user: User, plan_code: str) -> str:
    if not user.is_authenticated:
        raise BillingConfigurationError("Authentication required to start checkout.")
    if not stripe_is_configured():
        raise BillingConfigurationError("Stripe is not configured yet.")

    plan = get_plan_definition(plan_code)
    stripe.api_key = settings.STRIPE_SECRET_KEY
    success_url = _build_absolute_url(f"{reverse('pages:subscription')}?checkout=processing")
    cancel_url = _build_absolute_url(f"{reverse('pages:subscription')}?checkout=cancelled")

    checkout_session = stripe.checkout.Session.create(
        mode="payment",
        line_items=[{"price": plan.price_id, "quantity": 1}],
        success_url=success_url,
        cancel_url=cancel_url,
        client_reference_id=str(user.id),
        customer_email=user.email,
        metadata={"user_id": str(user.id), "plan_code": plan.code},
        payment_intent_data={"metadata": {"user_id": str(user.id), "plan_code": plan.code}},
    )

    logger.info(
        "Created Stripe checkout session for user=%s plan=%s session=%s",
        user.id,
        plan.code,
        checkout_session.id,
    )
    return checkout_session.url


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

    plan = get_plan_definition(plan_code)
    now = timezone.now()
    expiry = calculate_expiry(now, plan.code)

    user.subscriptions.filter(status__in=[SubscriptionStatus.PENDING, SubscriptionStatus.ACTIVE]).exclude(
        provider_subscription_id=session_payload["id"]
    ).update(
        status=SubscriptionStatus.CANCELED,
        current_period_end=now,
    )

    subscription, created = Subscription.objects.update_or_create(
        provider_subscription_id=session_payload["id"],
        defaults={
            "user": user,
            "provider": "stripe",
            "plan_code": plan.code,
            "status": SubscriptionStatus.ACTIVE,
            "provider_customer_id": session_payload.get("customer") or "",
            "current_period_start": now,
            "current_period_end": expiry,
        },
    )

    user.role = UserRole.PAID
    user.subscription_expires_at = expiry
    user.save(update_fields=["role", "subscription_expires_at"])
    send_subscription_activated_email(user, plan.title, expiry)

    logger.info(
        "Activated subscription for user=%s plan=%s session=%s created=%s expires_at=%s",
        user.id,
        plan.code,
        session_payload["id"],
        created,
        expiry.isoformat(),
    )
    return subscription


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
