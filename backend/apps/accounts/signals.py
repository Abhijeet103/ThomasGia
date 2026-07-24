from __future__ import annotations

from allauth.account.signals import user_signed_up
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone

from .emails import queue_welcome_email


def _queue_welcome_email_once(user) -> None:
    if user.welcome_email_sent_at or not user.email:
        return
    user.welcome_email_sent_at = timezone.now()
    user.save(update_fields=["welcome_email_sent_at"])
    queue_welcome_email(user.id)


@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    _queue_welcome_email_once(user)


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    _queue_welcome_email_once(user)
