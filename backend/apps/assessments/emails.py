from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail


logger = logging.getLogger(__name__)


def send_track_release_email(*, email: str, track_title: str) -> bool:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED or not email:
        return False

    subject = f"{track_title} is now live on MindMetric"
    message = (
        f"Hi there,\n\n"
        f"{track_title} is now available on MindMetric.\n\n"
        "You asked to be notified when this track opened. You can now sign in and start practicing.\n\n"
        f"Open MindMetric: {settings.SITE_URL}/practice/\n\n"
        f"If you need help, contact {settings.CONTACT_EMAIL}.\n\n"
        "MindMetric"
    )

    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        logger.info("Sent track release email track=%s email=%s", track_title, email)
        return True
    except Exception:
        logger.exception("Failed to send track release email track=%s email=%s", track_title, email)
        return False
