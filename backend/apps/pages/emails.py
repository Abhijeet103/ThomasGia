from django.conf import settings
from django.core.mail import send_mail


def send_sale_inquiry_notification(inquiry) -> None:
    if not settings.EMAIL_NOTIFICATIONS_ENABLED:
        return

    contact_label = inquiry.full_name or inquiry.email
    subject = f"New sales inquiry from {contact_label}"
    message = (
        "A new sales inquiry was submitted on MindMetric.\n\n"
        f"Contact name: {inquiry.full_name or 'N/A'}\n"
        f"Email: {inquiry.email}\n"
        f"Phone: {inquiry.phone or 'N/A'}\n"
        f"Organization: {inquiry.organization or 'N/A'}\n"
        f"Team size: {inquiry.team_size or 'N/A'}\n"
        f"Source page: {inquiry.source_page or 'N/A'}\n\n"
        "Message:\n"
        f"{inquiry.message}\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[settings.SALES_INQUIRY_NOTIFICATION_EMAIL],
        fail_silently=False,
    )
