from __future__ import annotations

from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    FREE = "free", "Free"
    PAID = "paid", "Paid"


class UserManager(DjangoUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superusers must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField(unique=True)
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.PROTECT, related_name="users", blank=True, null=True)
    role = models.CharField(max_length=16, choices=UserRole.choices, default=UserRole.FREE)
    is_tenant_admin = models.BooleanField(default=False)
    google_sub = models.CharField(max_length=255, blank=True, null=True, unique=True)
    subscription_expires_at = models.DateTimeField(blank=True, null=True)
    welcome_email_sent_at = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    @property
    def is_paid_user(self) -> bool:
        return self.role == UserRole.PAID

    @property
    def has_active_subscription(self) -> bool:
        return bool(self.subscription_expires_at and self.subscription_expires_at > timezone.now())

    @property
    def is_platform_admin(self) -> bool:
        return self.is_superuser
