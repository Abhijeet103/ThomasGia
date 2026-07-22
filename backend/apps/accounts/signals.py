from __future__ import annotations

from allauth.account.signals import user_signed_up
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .emails import send_login_alert_email, send_welcome_email


@receiver(user_signed_up)
def handle_user_signed_up(request, user, **kwargs):
    send_welcome_email(user)


@receiver(user_logged_in)
def handle_user_logged_in(sender, request, user, **kwargs):
    send_login_alert_email(user)
