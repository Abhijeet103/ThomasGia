from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from backend.apps.billing.services import calculate_expiry

from .models import (
    EnrollmentMode,
    EnrollmentSource,
    MembershipStatus,
    Tenant,
    TenantEnrollmentCode,
    TenantMembership,
    TenantStudentInvite,
    TenantType,
    TenantUser,
    TenantUserStatus,
)


@dataclass(frozen=True)
class TenantAccess:
    allowed: bool
    membership: TenantMembership | None
    requires_code: bool = False
    tenant_user: TenantUser | None = None


def is_institution_tenant(tenant: Tenant | None) -> bool:
    return bool(tenant and tenant.is_active and tenant.tenant_type == TenantType.INSTITUTION)


def get_or_create_tenant_user(*, tenant: Tenant | None, user) -> TenantUser | None:
    if tenant is None or not tenant.is_active or not getattr(user, "is_authenticated", False):
        return None

    normalized_email = user.email.strip().lower()
    tenant_user, created = TenantUser.objects.get_or_create(
        tenant=tenant,
        identity=user,
        defaults={
            "email": normalized_email,
            "status": TenantUserStatus.ACTIVE,
        },
    )
    changed_fields = []
    if tenant_user.email != normalized_email:
        tenant_user.email = normalized_email
        changed_fields.append("email")
    if changed_fields and not created:
        tenant_user.save(update_fields=(*changed_fields, "updated_at"))
    return tenant_user


def create_membership(*, tenant: Tenant, user, source: str) -> TenantMembership | None:
    if not tenant.default_plan_code:
        return None

    now = timezone.now()
    tenant_user = get_or_create_tenant_user(tenant=tenant, user=user)
    membership, created = TenantMembership.objects.get_or_create(
        tenant=tenant,
        user=user,
        defaults={
            "tenant_user": tenant_user,
            "status": MembershipStatus.ACTIVE,
            "plan_code": tenant.default_plan_code,
            "access_started_at": now,
            "access_expires_at": calculate_expiry(now, tenant.default_plan_code),
            "enrollment_source": source,
        },
    )
    if not created and membership.tenant_user_id != getattr(tenant_user, "id", None):
        membership.tenant_user = tenant_user
        membership.save(update_fields=("tenant_user", "updated_at"))
    if not created and membership.status == MembershipStatus.EXPIRED:
        membership.status = MembershipStatus.ACTIVE
        membership.plan_code = tenant.default_plan_code
        membership.access_started_at = now
        membership.access_expires_at = calculate_expiry(now, tenant.default_plan_code)
        membership.enrollment_source = source
        membership.save(
            update_fields=(
                "status",
                "plan_code",
                "access_started_at",
                "access_expires_at",
                "enrollment_source",
                "updated_at",
            )
        )
    return membership


def get_tenant_access(*, tenant: Tenant | None, user, auto_enroll: bool = True) -> TenantAccess:
    if not is_institution_tenant(tenant) or not getattr(user, "is_authenticated", False):
        return TenantAccess(True, None)
    tenant_user = get_or_create_tenant_user(tenant=tenant, user=user)
    if tenant_user and tenant_user.status != TenantUserStatus.ACTIVE:
        return TenantAccess(False, None, tenant_user=tenant_user)
    if user.is_superuser or (user.is_tenant_admin and user.tenant_id == tenant.id):
        return TenantAccess(True, None, tenant_user=tenant_user)

    membership = TenantMembership.objects.filter(tenant=tenant, user=user).first()
    if membership:
        if membership.tenant_user_id != getattr(tenant_user, "id", None):
            membership.tenant_user = tenant_user
            membership.save(update_fields=("tenant_user", "updated_at"))
        if membership.is_active:
            return TenantAccess(True, membership, tenant_user=tenant_user)
        if membership.status == MembershipStatus.ACTIVE:
            membership.status = MembershipStatus.EXPIRED
            membership.save(update_fields=("status", "updated_at"))
        return TenantAccess(
            False,
            membership,
            requires_code=tenant.enrollment_mode == EnrollmentMode.CODE_REQUIRED,
            tenant_user=tenant_user,
        )

    if not auto_enroll:
        return TenantAccess(
            False,
            None,
            requires_code=tenant.enrollment_mode == EnrollmentMode.CODE_REQUIRED,
            tenant_user=tenant_user,
        )

    invite = TenantStudentInvite.objects.filter(
        tenant=tenant,
        email__iexact=user.email,
        is_active=True,
        accepted_at__isnull=True,
    ).first()
    if invite:
        with transaction.atomic():
            membership = create_membership(tenant=tenant, user=user, source=EnrollmentSource.INVITE)
            if membership is None:
                return TenantAccess(False, None, tenant_user=tenant_user)
            invite.accepted_by = user
            invite.accepted_at = timezone.now()
            invite.save(update_fields=("accepted_by", "accepted_at", "updated_at"))
        return TenantAccess(True, membership, tenant_user=tenant_user)

    if tenant.enrollment_mode == EnrollmentMode.OPEN:
        membership = create_membership(tenant=tenant, user=user, source=EnrollmentSource.OPEN_LOGIN)
        return TenantAccess(membership is not None, membership, tenant_user=tenant_user)

    return TenantAccess(False, None, requires_code=True, tenant_user=tenant_user)


def redeem_enrollment_code(*, tenant: Tenant, user, raw_code: str) -> TenantMembership | None:
    code_hash = TenantEnrollmentCode.hash_code(raw_code)
    with transaction.atomic():
        enrollment_code = (
            TenantEnrollmentCode.objects.select_for_update()
            .filter(tenant=tenant, code_hash=code_hash)
            .first()
        )
        if enrollment_code is None or not enrollment_code.can_be_used:
            return None
        membership = create_membership(tenant=tenant, user=user, source=EnrollmentSource.CODE)
        if membership is None:
            return None
        if not membership.is_active:
            return None
        enrollment_code.usage_count += 1
        if enrollment_code.usage_count >= enrollment_code.max_uses:
            enrollment_code.is_active = False
        enrollment_code.save(update_fields=("usage_count", "is_active", "updated_at"))
        return membership


def tenant_allows_assessment(tenant: Tenant | None, assessment_type: str) -> bool:
    if tenant is None:
        return True
    return assessment_type in (tenant.allowed_assessments or [])
