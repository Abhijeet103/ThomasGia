from __future__ import annotations

import csv
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django import forms
from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone

from backend.apps.accounts.models import UserRole
from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import BillingPlan, BillingPlanCountryPrice, Subscription, SubscriptionStatus
from .services import calculate_expiry, sync_user_subscription_access


class BillingPlanDiscountForm(forms.Form):
    percentage = forms.IntegerField(
        min_value=1,
        max_value=90,
        label="Discount percentage",
        help_text="Enter a whole percentage from 1 to 90.",
        widget=forms.NumberInput(attrs={"min": 1, "max": 90, "step": 1}),
    )


class BillingPlanCountryPriceInline(admin.TabularInline):
    model = BillingPlanCountryPrice
    fields = ("country_code", "currency", "price", "sale_price", "is_active")
    extra = 0
    show_change_link = True


@admin.register(BillingPlan)
class BillingPlanAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "code",
        "price",
        "sale_price",
        "currency",
        "duration_label",
        "is_active",
        "updated_at",
    )
    list_editable = ("price", "sale_price", "is_active")
    list_filter = ("is_active", "currency")
    search_fields = ("title", "code")
    ordering = ("display_order", "id")
    readonly_fields = ("code",)
    actions = ("apply_percentage_discount", "clear_sale_discount")
    inlines = (BillingPlanCountryPriceInline,)
    fieldsets = (
        (
            "Plan",
            {
                "fields": (
                    "code",
                    "title",
                    "price",
                    "sale_price",
                    "currency",
                    "duration_label",
                    "summary",
                    "display_order",
                    "is_active",
                )
            },
        ),
    )

    def has_module_permission(self, request):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Apply percentage discount to selected plans")
    def apply_percentage_discount(self, request, queryset):
        if "confirm_discount" in request.POST:
            form = BillingPlanDiscountForm(request.POST)
            if form.is_valid():
                percentage = form.cleaned_data["percentage"]
                multiplier = (
                    Decimal("100") - Decimal(percentage)
                ) / Decimal("100")
                updated = 0
                for plan in queryset:
                    plan.sale_price = (plan.price * multiplier).quantize(
                        Decimal("0.01"),
                        rounding=ROUND_HALF_UP,
                    )
                    plan.full_clean()
                    plan.save(update_fields=("sale_price", "updated_at"))
                    updated += 1
                self.message_user(
                    request,
                    f"Applied a {percentage}% discount to {updated} plan(s).",
                    level=messages.SUCCESS,
                )
                return None
        else:
            form = BillingPlanDiscountForm()

        return render(
            request,
            "admin/billing/billingplan/apply_discount.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Apply percentage discount",
                "plans": queryset,
                "form": form,
                "action_name": "apply_percentage_discount",
                "cancel_url": reverse("admin:billing_billingplan_changelist"),
            },
        )

    @admin.action(description="Clear sale discount from selected plans")
    def clear_sale_discount(self, request, queryset):
        updated = queryset.exclude(sale_price__isnull=True).update(
            sale_price=None,
        )
        self.message_user(
            request,
            f"Cleared the sale discount from {updated} plan(s).",
            level=messages.SUCCESS,
        )


@admin.register(BillingPlanCountryPrice)
class BillingPlanCountryPriceAdmin(admin.ModelAdmin):
    list_display = (
        "plan",
        "country_code",
        "currency",
        "price",
        "sale_price",
        "is_active",
        "updated_at",
    )
    list_editable = ("price", "sale_price", "is_active")
    list_filter = ("country_code", "currency", "is_active")
    search_fields = ("plan__title", "plan__code", "country_code")
    autocomplete_fields = ("plan",)
    actions = ("apply_percentage_discount", "clear_sale_discount")

    def has_module_permission(self, request):
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_add_permission(self, request):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    @admin.action(description="Apply percentage discount to selected regional prices")
    def apply_percentage_discount(self, request, queryset):
        if "confirm_discount" in request.POST:
            form = BillingPlanDiscountForm(request.POST)
            if form.is_valid():
                percentage = form.cleaned_data["percentage"]
                multiplier = (Decimal("100") - Decimal(percentage)) / Decimal("100")
                updated = 0
                for regional_price in queryset:
                    regional_price.sale_price = (
                        regional_price.price * multiplier
                    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    regional_price.full_clean()
                    regional_price.save(update_fields=("sale_price", "updated_at"))
                    updated += 1
                self.message_user(
                    request,
                    f"Applied a {percentage}% discount to {updated} regional price(s).",
                    level=messages.SUCCESS,
                )
                return None
        else:
            form = BillingPlanDiscountForm()

        return render(
            request,
            "admin/billing/billingplan/apply_discount.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "title": "Apply regional percentage discount",
                "plans": queryset,
                "form": form,
                "action_name": "apply_percentage_discount",
                "cancel_url": reverse(
                    "admin:billing_billingplancountryprice_changelist"
                ),
            },
        )

    @admin.action(description="Clear sale discount from selected regional prices")
    def clear_sale_discount(self, request, queryset):
        updated = queryset.exclude(sale_price__isnull=True).update(sale_price=None)
        self.message_user(
            request,
            f"Cleared the sale discount from {updated} regional price(s).",
            level=messages.SUCCESS,
        )


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
class SubscriptionAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("tenant", "user", "provider", "plan_code", "status", "current_period_end")
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
