from django.db import models


class SaleInquiry(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        CLOSED = "closed", "Closed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="sale_inquiries", blank=True, null=True)
    full_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField()
    phone = models.CharField(max_length=64, blank=True)
    organization = models.CharField(max_length=255, blank=True)
    team_size = models.CharField(max_length=64, blank=True)
    message = models.TextField()
    source_page = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    contacted_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        label = self.full_name or self.email
        return f"{label} ({self.email})"


class TestSuggestion(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        REVIEWED = "reviewed", "Reviewed"
        PLANNED = "planned", "Planned"
        CLOSED = "closed", "Closed"

    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="test_suggestions", blank=True, null=True)
    user = models.ForeignKey("accounts.User", on_delete=models.SET_NULL, related_name="test_suggestions", blank=True, null=True)
    email = models.EmailField()
    requested_test = models.CharField(max_length=255)
    message = models.TextField(blank=True)
    source_page = models.CharField(max_length=64, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NEW)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.requested_test} ({self.email})"
