from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "provider", "plan_code", "status", "current_period_end")
    list_filter = ("provider", "status", "plan_code")
    search_fields = ("user__email", "provider_customer_id", "provider_subscription_id")

