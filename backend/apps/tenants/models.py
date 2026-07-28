from __future__ import annotations

import hashlib
import hmac
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class TenantType(models.TextChoices):
    PLATFORM = "platform", "Platform"
    INSTITUTION = "institution", "Institution"


class EnrollmentMode(models.TextChoices):
    OPEN = "open", "Open login"
    CODE_REQUIRED = "code_required", "Enrollment code required"


class TenantPlan(models.TextChoices):
    WEEKLY = "weekly", "Weekly"
    MONTHLY = "monthly", "Monthly"
    YEARLY = "yearly", "Yearly"


class MembershipStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class TenantUserStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SUSPENDED = "suspended", "Suspended"


class EnrollmentSource(models.TextChoices):
    OPEN_LOGIN = "open_login", "Open login"
    CODE = "code", "Enrollment code"
    INVITE = "invite", "Pre-added student"
    ADMIN = "admin", "Admin"


class Tenant(models.Model):
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    primary_domain = models.CharField(max_length=255, unique=True)
    tenant_type = models.CharField(max_length=16, choices=TenantType.choices, default=TenantType.INSTITUTION)
    subdomain_prefix = models.SlugField(max_length=63, unique=True, blank=True, null=True)
    enrollment_mode = models.CharField(max_length=24, choices=EnrollmentMode.choices, default=EnrollmentMode.OPEN)
    default_plan_code = models.CharField(
        "default plan",
        max_length=16,
        choices=TenantPlan.choices,
        blank=True,
        null=True,
        default=None,
        help_text=(
            "Optional plan automatically granted when a member joins. "
            "Leave blank to require a manual membership grant."
        ),
    )
    allowed_assessments = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name

    @property
    def is_platform_tenant(self) -> bool:
        return self.tenant_type == TenantType.PLATFORM

    def clean(self):
        super().clean()
        if self.tenant_type == TenantType.INSTITUTION and not self.subdomain_prefix:
            raise ValidationError({"subdomain_prefix": "Institution tenants require a subdomain prefix."})
        if self.tenant_type == TenantType.PLATFORM and self.subdomain_prefix:
            raise ValidationError({"subdomain_prefix": "The platform tenant cannot use an institution prefix."})

    def save(self, *args, **kwargs):
        if self.tenant_type == TenantType.INSTITUTION and self.subdomain_prefix:
            base_domain = getattr(settings, "TENANT_BASE_DOMAIN", "mindmetric.store").strip().lower()
            self.primary_domain = f"{self.subdomain_prefix.lower()}.{base_domain}"
        super().save(*args, **kwargs)


class TenantUser(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="tenant_users")
    identity = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tenant_users",
    )
    email = models.EmailField()
    status = models.CharField(
        max_length=16,
        choices=TenantUserStatus.choices,
        default=TenantUserStatus.ACTIVE,
    )
    joined_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("tenant", "identity"), name="unique_tenant_user_identity"),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "joined_at")),
            models.Index(fields=("tenant", "email")),
            models.Index(fields=("identity", "status")),
        ]
        ordering = ("tenant__name", "email")

    def __str__(self) -> str:
        return f"{self.email} at {self.tenant.name}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


class TenantMembership(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tenant_memberships")
    tenant_user = models.OneToOneField(
        TenantUser,
        on_delete=models.CASCADE,
        related_name="membership",
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=16, choices=MembershipStatus.choices, default=MembershipStatus.ACTIVE)
    plan_code = models.CharField(max_length=16, choices=TenantPlan.choices)
    access_started_at = models.DateTimeField()
    access_expires_at = models.DateTimeField()
    enrollment_source = models.CharField(max_length=24, choices=EnrollmentSource.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("tenant", "user"), name="unique_tenant_membership"),
        ]
        indexes = [
            models.Index(fields=("tenant", "status", "access_expires_at")),
            models.Index(fields=("user", "status", "access_expires_at")),
        ]
        ordering = ("-created_at",)

    def __str__(self) -> str:
        return f"{self.user.email} at {self.tenant.name}"

    def clean(self):
        super().clean()
        if self.tenant_user_id and (
            self.tenant_user.tenant_id != self.tenant_id
            or self.tenant_user.identity_id != self.user_id
        ):
            raise ValidationError(
                {"tenant_user": "The tenant user must match this membership's tenant and identity."}
            )

    def save(self, *args, **kwargs):
        if self.tenant_user_id is None and self.tenant_id and self.user_id:
            self.tenant_user, _ = TenantUser.objects.get_or_create(
                tenant_id=self.tenant_id,
                identity_id=self.user_id,
                defaults={
                    "email": self.user.email.strip().lower(),
                    "status": TenantUserStatus.ACTIVE,
                },
            )
        super().save(*args, **kwargs)

    @property
    def is_active(self) -> bool:
        return self.status == MembershipStatus.ACTIVE and self.access_expires_at > timezone.now()


class TenantEnrollmentCode(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="enrollment_codes")
    label = models.CharField(max_length=120, blank=True)
    code = models.CharField(
        max_length=32,
        blank=True,
        default="",
        editable=False,
        help_text="Full enrollment code retained for display to platform administrators.",
    )
    code_prefix = models.CharField(max_length=12)
    code_hash = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    max_uses = models.PositiveIntegerField(default=1)
    usage_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_tenant_enrollment_codes",
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("tenant", "is_active", "expires_at")),
        ]

    def __str__(self) -> str:
        return f"{self.tenant.name}: {self.label or self.code_prefix}"

    @staticmethod
    def hash_code(raw_code: str) -> str:
        normalized = raw_code.strip().upper().encode("utf-8")
        key = settings.SECRET_KEY.encode("utf-8")
        return hmac.new(key, normalized, hashlib.sha256).hexdigest()

    @classmethod
    def generate_raw_code(cls) -> str:
        return f"MM-{secrets.token_hex(4).upper()}"

    @property
    def can_be_used(self) -> bool:
        if not self.is_active or self.usage_count >= self.max_uses:
            return False
        return not self.expires_at or self.expires_at > timezone.now()


class TenantStudentInvite(models.Model):
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="student_invites")
    email = models.EmailField()
    full_name = models.CharField(max_length=255, blank=True)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="accepted_tenant_invites",
        blank=True,
        null=True,
    )
    accepted_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("tenant", "email"), name="unique_tenant_student_invite"),
        ]
        indexes = [
            models.Index(fields=("tenant", "email", "is_active")),
        ]
        ordering = ("email",)

    def __str__(self) -> str:
        return f"{self.email} invited to {self.tenant.name}"

    def save(self, *args, **kwargs):
        self.email = self.email.strip().lower()
        super().save(*args, **kwargs)
