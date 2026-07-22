from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail


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


def send_login_alert_email(user) -> None:
    _send_email(
        subject="New login to your MindMetric account",
        message=(
            f"Hi {user.first_name or 'there'},\n\n"
            "We noticed a new login to your MindMetric account.\n\n"
            f"Account: {user.email}\n"
            "If this was you, no action is needed.\n"
            f"If this was not you, contact us immediately at {settings.CONTACT_EMAIL}.\n\n"
            "MindMetric"
        ),
        recipients=[user.email],
    )


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
