from django.contrib import admin

from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import SaleInquiry


@admin.register(SaleInquiry)
class SaleInquiryAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("tenant", "full_name", "email", "phone", "source_page", "status", "created_at")
    list_filter = ("status", "source_page", "created_at")
    search_fields = ("full_name", "email", "phone", "message")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "tenant",
        "full_name",
        "email",
        "phone",
        "source_page",
        "status",
        "message",
        "notes",
        "contacted_at",
        "created_at",
        "updated_at",
    )
