from __future__ import annotations

import csv
from datetime import timedelta

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone

from backend.apps.accounts.models import UserRole

from .models import Subscription, SubscriptionStatus
from .services import calculate_expiry, sync_user_subscription_access


def _ensure_manual_subscription(subscription: Subscription, plan_code: str, extra_days: int | None = None) -> None:
    now = timezone.now()
    subscription.provider = subscription.provider or "admin"
    subscription.plan_code = plan_code
    subscription.status = SubscriptionStatus.ACTIVE
    subscription.current_period_start = subscription.current_period_start or now
    if extra_days is not None:
        base = subscription.current_period_end if subscription.current_period_end and subscription.current_period_end > now else now
        subscription.current_period_end = base + timedelta(days=extra_days)
    else:
        subscription.current_period_end = calculate_expiry(now, plan_code)
    subscription.save()

    user = subscription.user
    user.role = UserRole.PAID
    user.subscription_expires_at = subscription.current_period_end
    user.save(update_fields=["role", "subscription_expires_at"])


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "plan_code", "status", "current_period_end")
    list_filter = ("provider", "status", "plan_code")
    search_fields = ("user__email", "provider_customer_id", "provider_subscription_id")
    actions = (
        "activate_weekly_plan",
        "activate_monthly_plan",
        "activate_yearly_plan",
        "extend_selected_by_30_days",
        "cancel_selected_subscriptions",
        "reset_selected_users_to_free",
        "resync_selected_users",
        "delete_broken_subscriptions",
        "export_selected_subscriptions_csv",
    )

    @admin.action(description="Activate weekly plan")
    def activate_weekly_plan(self, request, queryset):
        updated = 0
        for subscription in queryset.select_related("user"):
            _ensure_manual_subscription(subscription, "weekly")
            updated += 1
        self.message_user(request, f"Activated weekly access for {updated} subscription(s).", level=messages.SUCCESS)

    @admin.action(description="Activate monthly plan")
    def activate_monthly_plan(self, request, queryset):
        updated = 0
        for subscription in queryset.select_related("user"):
            _ensure_manual_subscription(subscription, "monthly")
            updated += 1
        self.message_user(request, f"Activated monthly access for {updated} subscription(s).", level=messages.SUCCESS)

    @admin.action(description="Activate yearly plan")
    def activate_yearly_plan(self, request, queryset):
        updated = 0
        for subscription in queryset.select_related("user"):
            _ensure_manual_subscription(subscription, "yearly")
            updated += 1
        self.message_user(request, f"Activated yearly access for {updated} subscription(s).", level=messages.SUCCESS)

    @admin.action(description="Extend selected subscriptions by 30 days")
    def extend_selected_by_30_days(self, request, queryset):
        updated = 0
        for subscription in queryset.select_related("user"):
            plan_code = subscription.plan_code if subscription.plan_code in {"weekly", "monthly", "yearly"} else "monthly"
            _ensure_manual_subscription(subscription, plan_code, extra_days=30)
            updated += 1
        self.message_user(request, f"Extended {updated} subscription(s) by 30 days.", level=messages.SUCCESS)

    @admin.action(description="Cancel selected subscriptions")
    def cancel_selected_subscriptions(self, request, queryset):
        now = timezone.now()
        updated = 0
        users_to_resync = []
        for subscription in queryset.select_related("user"):
            subscription.status = SubscriptionStatus.CANCELED
            subscription.current_period_end = now
            subscription.save(update_fields=["status", "current_period_end", "updated_at"])
            users_to_resync.append(subscription.user)
            updated += 1
        for user in users_to_resync:
            sync_user_subscription_access(user)
        self.message_user(request, f"Canceled {updated} subscription(s).", level=messages.SUCCESS)

    @admin.action(description="Reset selected users to free tier")
    def reset_selected_users_to_free(self, request, queryset):
        updated = 0
        for subscription in queryset.select_related("user"):
            user = subscription.user
            subscription.status = SubscriptionStatus.CANCELED
            subscription.current_period_end = timezone.now()
            subscription.save(update_fields=["status", "current_period_end", "updated_at"])
            user.role = UserRole.FREE
            user.subscription_expires_at = None
            user.save(update_fields=["role", "subscription_expires_at"])
            updated += 1
        self.message_user(request, f"Reset {updated} user(s) to free tier.", level=messages.SUCCESS)

    @admin.action(description="Resync selected users' billing status")
    def resync_selected_users(self, request, queryset):
        seen_user_ids = set()
        updated = 0
        for subscription in queryset.select_related("user"):
            if subscription.user_id in seen_user_ids:
                continue
            sync_user_subscription_access(subscription.user)
            seen_user_ids.add(subscription.user_id)
            updated += 1
        self.message_user(request, f"Resynced billing access for {updated} user(s).", level=messages.SUCCESS)

    @admin.action(description="Delete broken subscriptions")
    def delete_broken_subscriptions(self, request, queryset):
        broken = queryset.filter(provider_subscription_id="", provider_customer_id="", status=SubscriptionStatus.PENDING)
        deleted_count = broken.count()
        broken.delete()
        self.message_user(request, f"Deleted {deleted_count} broken pending subscription(s).", level=messages.SUCCESS)

    @admin.action(description="Export selected subscriptions as CSV")
    def export_selected_subscriptions_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="subscriptions.csv"'
        writer = csv.writer(response)
        writer.writerow(["email", "provider", "plan_code", "status", "period_start", "period_end"])
        for subscription in queryset.select_related("user"):
            writer.writerow(
                [
                    subscription.user.email,
                    subscription.provider,
                    subscription.plan_code,
                    subscription.status,
                    subscription.current_period_start.isoformat() if subscription.current_period_start else "",
                    subscription.current_period_end.isoformat() if subscription.current_period_end else "",
                ]
            )
        return response
