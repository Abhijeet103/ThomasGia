from __future__ import annotations

import logging
from threading import Thread

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import User


logger = logging.getLogger(__name__)


def _send_email(subject: str, message: str, recipients: list[str]) -> None:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED or not recipients:
        return
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipients,
            fail_silently=False,
        )
        logger.info("Sent transactional email subject=%s recipients=%s", subject, len(recipients))
    except Exception:
        logger.exception("Failed to send transactional email subject=%s", subject)


def send_welcome_email(user) -> None:
    _send_email(
        subject="Welcome to MindMetric",
        message=(
            f"Hi {user.first_name or 'there'},\n\n"
            "Welcome to MindMetric.\n\n"
            "Your account is ready and you can now practice Thomas GIA and CCAT-style assessments, "
            "review your dashboard, and upgrade whenever you need unlimited access.\n\n"
            f"If you need help, reply to {settings.CONTACT_EMAIL}.\n\n"
            "MindMetric"
        ),
        recipients=[user.email],
    )


def _send_welcome_email_for_user_id(user_id: int) -> None:
    try:
        user = User.objects.only("id", "email", "first_name").get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("Skipped welcome email because user id=%s no longer exists", user_id)
        return
    send_welcome_email(user)


def queue_welcome_email(user_id: int) -> None:
    def _spawn() -> None:
        thread = Thread(target=_send_welcome_email_for_user_id, args=(user_id,), daemon=True)
        thread.start()

    transaction.on_commit(_spawn)


def send_subscription_activated_email(user, plan_title: str, expires_at) -> None:
    expiry_text = expires_at.strftime("%B %d, %Y %H:%M %Z") if expires_at else "your current billing period"
    _send_email(
        subject="Your MindMetric subscription is active",
        message=(
            f"Hi {user.first_name or 'there'},\n\n"
            f"Your {plan_title} MindMetric plan is now active.\n\n"
            f"Access expires on: {expiry_text}\n\n"
            "You can now access unlimited full tests and module-wise tests during the active period.\n\n"
            "MindMetric"
        ),
        recipients=[user.email],
    )


def send_subscription_canceled_email(user) -> None:
    _send_email(
        subject="Your MindMetric subscription was canceled",
        message=(
            f"Hi {user.first_name or 'there'},\n\n"
            "Your MindMetric subscription has been canceled and your account has been moved back to the free tier.\n\n"
            f"If you need help or think this was a mistake, contact {settings.CONTACT_EMAIL}.\n\n"
            "MindMetric"
        ),
        recipients=[user.email],
    )
