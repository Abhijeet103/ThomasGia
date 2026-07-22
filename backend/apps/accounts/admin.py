from __future__ import annotations

import csv
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.http import HttpResponse
from django.utils import timezone

from backend.apps.assessments.models import Attempt, AttemptStatus, SectionProgress
from backend.apps.assessments.services import recompute_section_progress_for_user
from backend.apps.billing.models import Subscription, SubscriptionStatus
from backend.apps.billing.services import calculate_expiry, sync_user_subscription_access

from .models import User, UserRole


def _activate_manual_subscription_for_user(user: User, plan_code: str) -> None:
    now = timezone.now()
    expiry = calculate_expiry(now, plan_code)
    Subscription.objects.update_or_create(
        user=user,
        provider="admin",
        status=SubscriptionStatus.ACTIVE,
        defaults={
            "plan_code": plan_code,
            "provider_customer_id": "",
            "provider_subscription_id": f"admin-{user.id}-{plan_code}",
            "current_period_start": now,
            "current_period_end": expiry,
        },
    )
    user.role = UserRole.PAID
    user.subscription_expires_at = expiry
    user.save(update_fields=["role", "subscription_expires_at"])


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "subscription_expires_at", "is_staff")
    search_fields = ("email", "first_name", "last_name")
    actions = (
        "mark_selected_users_as_paid",
        "grant_yearly_access",
        "extend_selected_subscriptions_by_30_days",
        "reset_selected_users_to_free",
        "resync_billing_status",
        "promote_to_admin_access",
        "export_user_results_csv",
        "recompute_dashboard_metrics",
    )
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("first_name", "last_name", "role", "google_sub", "subscription_expires_at")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "role", "is_staff", "is_superuser"),
            },
        ),
    )

    @admin.action(description="Mark selected users as paid")
    def mark_selected_users_as_paid(self, request, queryset):
        updated = 0
        for user in queryset:
            _activate_manual_subscription_for_user(user, "monthly")
            updated += 1
        self.message_user(request, f"Marked {updated} user(s) as paid on a monthly admin plan.", level=messages.SUCCESS)

    @admin.action(description="Grant yearly access")
    def grant_yearly_access(self, request, queryset):
        updated = 0
        for user in queryset:
            _activate_manual_subscription_for_user(user, "yearly")
            updated += 1
        self.message_user(request, f"Granted yearly access to {updated} user(s).", level=messages.SUCCESS)

    @admin.action(description="Extend selected subscriptions by 30 days")
    def extend_selected_subscriptions_by_30_days(self, request, queryset):
        now = timezone.now()
        updated = 0
        for user in queryset:
            base = user.subscription_expires_at if user.subscription_expires_at and user.subscription_expires_at > now else now
            new_expiry = base + timedelta(days=30)
            subscription, _ = Subscription.objects.get_or_create(
                user=user,
                provider="admin",
                defaults={
                    "plan_code": "monthly",
                    "status": SubscriptionStatus.ACTIVE,
                    "provider_subscription_id": f"admin-{user.id}-monthly",
                },
            )
            subscription.status = SubscriptionStatus.ACTIVE
            subscription.current_period_start = subscription.current_period_start or now
            subscription.current_period_end = new_expiry
            subscription.save()
            user.role = UserRole.PAID
            user.subscription_expires_at = new_expiry
            user.save(update_fields=["role", "subscription_expires_at"])
            updated += 1
        self.message_user(request, f"Extended access by 30 days for {updated} user(s).", level=messages.SUCCESS)

    @admin.action(description="Reset selected users to free tier")
    def reset_selected_users_to_free(self, request, queryset):
        now = timezone.now()
        updated = 0
        for user in queryset:
            user.subscriptions.filter(status=SubscriptionStatus.ACTIVE).update(
                status=SubscriptionStatus.CANCELED,
                current_period_end=now,
            )
            user.role = UserRole.FREE
            user.subscription_expires_at = None
            user.save(update_fields=["role", "subscription_expires_at"])
            updated += 1
        self.message_user(request, f"Reset {updated} user(s) to free tier.", level=messages.SUCCESS)

    @admin.action(description="Resync billing status")
    def resync_billing_status(self, request, queryset):
        updated = 0
        for user in queryset:
            sync_user_subscription_access(user)
            updated += 1
        self.message_user(request, f"Resynced billing status for {updated} user(s).", level=messages.SUCCESS)

    @admin.action(description="Promote to admin access")
    def promote_to_admin_access(self, request, queryset):
        updated = queryset.update(is_staff=True)
        self.message_user(request, f"Granted admin-panel access to {updated} user(s).", level=messages.SUCCESS)

    @admin.action(description="Export user results as CSV")
    def export_user_results_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="user_results.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "email",
                "role",
                "subscription_expires_at",
                "attempts_total",
                "attempts_completed",
                "tests_in_progress",
                "section_progress_rows",
            ]
        )
        for user in queryset:
            attempts = Attempt.objects.filter(user=user)
            writer.writerow(
                [
                    user.email,
                    user.role,
                    user.subscription_expires_at.isoformat() if user.subscription_expires_at else "",
                    attempts.count(),
                    attempts.filter(status=AttemptStatus.COMPLETED).count(),
                    attempts.filter(status=AttemptStatus.IN_PROGRESS).count(),
                    SectionProgress.objects.filter(user=user).count(),
                ]
            )
        return response

    @admin.action(description="Recompute dashboard metrics")
    def recompute_dashboard_metrics(self, request, queryset):
        updated = 0
        for user in queryset:
            updated += recompute_section_progress_for_user(user)
        self.message_user(request, f"Recomputed section dashboard metrics across {updated} progress row(s).", level=messages.SUCCESS)
