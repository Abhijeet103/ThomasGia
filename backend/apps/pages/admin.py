from django.contrib import admin

from .models import SaleInquiry


@admin.register(SaleInquiry)
class SaleInquiryAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "phone", "source_page", "status", "created_at")
    list_filter = ("status", "source_page", "created_at")
    search_fields = ("full_name", "email", "phone", "message")
    readonly_fields = ("created_at", "updated_at")
    fields = (
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
