from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse
from django.utils import timezone

from backend.apps.assessments.config import PRACTICE_TRACK_LIBRARY
from backend.apps.assessments.models import PracticeTrackVisibility

from .forms import (
    ASSESSMENT_STATE_FIELD_NAMES,
    EnrollmentCodeGenerateForm,
    StudentInviteBulkForm,
    TenantAdminForm,
    TenantAdminUserCreateForm,
    TenantCreateForm,
)
from .models import (
    MembershipStatus,
    Tenant,
    TenantEnrollmentCode,
    TenantMembership,
    TenantStudentInvite,
    TenantUser,
)
from .services import create_membership, get_or_create_tenant_user

User = get_user_model()


class PlatformSuperuserAdminMixin:
    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class TenantMembershipInline(admin.TabularInline):
    model = TenantMembership
    extra = 0
    fields = (
        "user",
        "tenant_user",
        "status",
        "plan_code",
        "access_started_at",
        "access_expires_at",
        "enrollment_source",
    )
    readonly_fields = ("enrollment_source",)
    show_change_link = True


@admin.register(Tenant)
class TenantAdmin(PlatformSuperuserAdminMixin, admin.ModelAdmin):
    form = TenantAdminForm
    list_display = (
        "name",
        "subdomain_prefix",
        "primary_domain",
        "enrollment_mode",
        "default_plan_code",
        "assessment_summary",
        "is_active",
    )
    search_fields = ("name", "slug", "subdomain_prefix", "primary_domain")
    list_filter = ("tenant_type", "enrollment_mode", "default_plan_code", "is_active")
    readonly_fields = ("primary_domain", "created_at", "updated_at")
    fieldsets = (
        (
            "Tenant identity",
            {
                "fields": (
                    "name",
                    "slug",
                    "tenant_type",
                    "subdomain_prefix",
                    "primary_domain",
                    "is_active",
                )
            },
        ),
        (
            "Institution access",
            {
                "fields": (
                    "enrollment_mode",
                    "default_plan_code",
                )
            },
        ),
        (
            "Assessment allocation and visibility",
            {
                "description": (
                    "Manage each assessment here. Not allocated blocks access; "
                    "Accessible publishes it; Upcoming shows a coming-soon card; "
                    "Hidden keeps it allocated without showing it on the frontend."
                ),
                "fields": ASSESSMENT_STATE_FIELD_NAMES,
            },
        ),
        ("Audit", {"fields": ("created_at", "updated_at")}),
    )
    change_list_template = "admin/tenants/tenant/change_list.html"
    change_form_template = "admin/tenants/tenant/change_form.html"
    inlines = (TenantMembershipInline,)
    actions = ("activate_selected_tenants", "suspend_selected_tenants")

    def get_urls(self):
        custom_urls = [
            path("create/", self.admin_site.admin_view(self.create_tenant_view), name="tenants_tenant_create"),
            path(
                "<path:object_id>/create-admin/",
                self.admin_site.admin_view(self.create_tenant_admin_view),
                name="tenants_tenant_create_admin",
            ),
            path(
                "<path:object_id>/generate-code/",
                self.admin_site.admin_view(self.generate_code_view),
                name="tenants_tenant_generate_code",
            ),
            path(
                "<path:object_id>/add-students/",
                self.admin_site.admin_view(self.add_students_view),
                name="tenants_tenant_add_students",
            ),
        ]
        return custom_urls + super().get_urls()

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("assessment_tracks")

    @admin.display(description="Assessments")
    def assessment_summary(self, obj):
        allowed_assessments = set(obj.allowed_assessments or [])
        tracks_by_key = {
            track.assessment_type: track
            for track in obj.assessment_tracks.all()
        }
        summary = []
        for assessment_key, config in PRACTICE_TRACK_LIBRARY.items():
            if assessment_key not in allowed_assessments:
                continue
            track = tracks_by_key.get(assessment_key)
            visibility_state = (
                track.visibility_state
                if track
                else config.get(
                    "default_visibility_state",
                    PracticeTrackVisibility.ACCESSIBLE,
                )
            )
            summary.append(
                f"{config['title']}: {PracticeTrackVisibility(visibility_state).label}"
            )
        return ", ".join(summary) or "None allocated"

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        form.sync_assessment_tracks(obj)


    @admin.action(description="Activate selected tenants")
    def activate_selected_tenants(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"Activated {count} tenant(s).", level=messages.SUCCESS)

    @admin.action(description="Suspend selected tenants")
    def suspend_selected_tenants(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"Suspended {count} tenant(s).", level=messages.SUCCESS)

    def _superuser_only(self, request, message):
        if request.user.is_superuser:
            return None
        self.message_user(request, message, level=messages.ERROR)
        return redirect("admin:tenants_tenant_changelist")

    def create_tenant_view(self, request: HttpRequest) -> HttpResponse:
        denied = self._superuser_only(request, "Only platform superusers can create tenants.")
        if denied:
            return denied
        if request.method == "POST":
            form = TenantCreateForm(request.POST)
            if form.is_valid():
                tenant = form.save()
                self.message_user(request, f"Created tenant {tenant.name}.", level=messages.SUCCESS)
                return redirect(reverse("admin:tenants_tenant_change", args=[tenant.pk]))
        else:
            form = TenantCreateForm()
        return render(
            request,
            "admin/tenants/tenant/create_tenant.html",
            {**self.admin_site.each_context(request), "opts": self.model._meta, "title": "Create tenant", "form": form},
        )

    def create_tenant_admin_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        denied = self._superuser_only(request, "Only platform superusers can create tenant admins.")
        if denied:
            return denied
        tenant = get_object_or_404(Tenant, pk=object_id)
        if request.method == "POST":
            form = TenantAdminUserCreateForm(request.POST)
            if form.is_valid():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                    tenant=tenant,
                    is_staff=True,
                    is_tenant_admin=True,
                    is_superuser=False,
                )
                get_or_create_tenant_user(tenant=tenant, user=user)
                self.message_user(request, f"Created tenant admin {user.email}.", level=messages.SUCCESS)
                return redirect(reverse("admin:accounts_user_change", args=[user.pk]))
        else:
            form = TenantAdminUserCreateForm()
        return render(
            request,
            "admin/tenants/tenant/create_tenant_admin.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "original": tenant,
                "tenant": tenant,
                "title": f"Create tenant admin for {tenant.name}",
                "form": form,
            },
        )

    def generate_code_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        denied = self._superuser_only(request, "Only platform superusers can generate enrollment codes.")
        if denied:
            return denied
        tenant = get_object_or_404(Tenant, pk=object_id)
        if request.method == "POST":
            form = EnrollmentCodeGenerateForm(request.POST)
            if form.is_valid():
                raw_code = TenantEnrollmentCode.generate_raw_code()
                TenantEnrollmentCode.objects.create(
                    tenant=tenant,
                    label=form.cleaned_data["label"],
                    code=raw_code,
                    code_prefix=raw_code[:7],
                    code_hash=TenantEnrollmentCode.hash_code(raw_code),
                    expires_at=form.cleaned_data["expires_at"],
                    max_uses=form.cleaned_data["max_uses"],
                    created_by=request.user,
                )
                self.message_user(
                    request,
                    f"Enrollment code created: {raw_code}. Store it now; it cannot be viewed again.",
                    level=messages.SUCCESS,
                )
                return redirect(reverse("admin:tenants_tenantenrollmentcode_changelist"))
        else:
            form = EnrollmentCodeGenerateForm()
        return render(
            request,
            "admin/tenants/tenant/simple_action_form.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "tenant": tenant,
                "title": f"Generate enrollment code for {tenant.name}",
                "submit_label": "Generate code",
                "form": form,
            },
        )

    def add_students_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        denied = self._superuser_only(request, "Only platform superusers can pre-add students.")
        if denied:
            return denied
        tenant = get_object_or_404(Tenant, pk=object_id)
        if request.method == "POST":
            form = StudentInviteBulkForm(request.POST)
            if form.is_valid():
                created = 0
                for email, full_name in form.cleaned_data["students"]:
                    _, was_created = TenantStudentInvite.objects.update_or_create(
                        tenant=tenant,
                        email=email,
                        defaults={"full_name": full_name, "is_active": True},
                    )
                    created += int(was_created)
                self.message_user(request, f"Added {created} new student(s).", level=messages.SUCCESS)
                return redirect(reverse("admin:tenants_tenantstudentinvite_changelist"))
        else:
            form = StudentInviteBulkForm()
        return render(
            request,
            "admin/tenants/tenant/simple_action_form.html",
            {
                **self.admin_site.each_context(request),
                "opts": self.model._meta,
                "tenant": tenant,
                "title": f"Pre-add students to {tenant.name}",
                "submit_label": "Add students",
                "form": form,
            },
        )

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")
        if obj and request.user.is_superuser:
            context.update(
                {
                    "tenant_admin_create_url": reverse("admin:tenants_tenant_create_admin", args=[obj.pk]),
                    "tenant_generate_code_url": reverse("admin:tenants_tenant_generate_code", args=[obj.pk]),
                    "tenant_add_students_url": reverse("admin:tenants_tenant_add_students", args=[obj.pk]),
                }
            )
        return super().render_change_form(request, context, *args, **kwargs)


@admin.register(TenantMembership)
class TenantMembershipAdmin(PlatformSuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("tenant_user", "user", "tenant", "status", "plan_code", "access_started_at", "access_expires_at", "enrollment_source")
    list_filter = ("tenant", "status", "plan_code", "enrollment_source")
    search_fields = ("user__email", "tenant__name", "tenant__subdomain_prefix")
    readonly_fields = ("created_at", "updated_at")
    actions = ("extend_from_now", "revoke_selected")

    @admin.action(description="Restart selected memberships using tenant plan")
    def extend_from_now(self, request, queryset):
        count = 0
        skipped = 0
        for membership in queryset.select_related("tenant", "user"):
            if not membership.tenant.default_plan_code:
                skipped += 1
                continue
            membership.status = MembershipStatus.EXPIRED
            membership.save(update_fields=("status", "updated_at"))
            create_membership(tenant=membership.tenant, user=membership.user, source="admin")
            count += 1
        self.message_user(request, f"Restarted {count} membership(s).", level=messages.SUCCESS)
        if skipped:
            self.message_user(
                request,
                f"Skipped {skipped} membership(s) because their tenant has no default plan.",
                level=messages.WARNING,
            )

    @admin.action(description="Revoke selected memberships")
    def revoke_selected(self, request, queryset):
        count = queryset.update(status=MembershipStatus.REVOKED, access_expires_at=timezone.now())
        self.message_user(request, f"Revoked {count} membership(s).", level=messages.SUCCESS)


@admin.register(TenantUser)
class TenantUserAdmin(PlatformSuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("email", "tenant", "identity", "status", "joined_at", "last_seen_at")
    list_filter = ("tenant", "status")
    search_fields = ("email", "identity__email", "tenant__name", "tenant__subdomain_prefix")
    readonly_fields = ("tenant", "identity", "email", "joined_at", "last_seen_at", "updated_at")
    actions = ("activate_selected", "suspend_selected")

    def has_add_permission(self, request):
        return False

    @admin.action(description="Activate selected tenant users")
    def activate_selected(self, request, queryset):
        count = queryset.update(status="active")
        self.message_user(request, f"Activated {count} tenant user(s).", level=messages.SUCCESS)

    @admin.action(description="Suspend selected tenant users")
    def suspend_selected(self, request, queryset):
        count = queryset.update(status="suspended")
        self.message_user(request, f"Suspended {count} tenant user(s).", level=messages.SUCCESS)


@admin.register(TenantEnrollmentCode)
class TenantEnrollmentCodeAdmin(PlatformSuperuserAdminMixin, admin.ModelAdmin):
    list_display = (
        "label",
        "tenant",
        "enrollment_code",
        "usage_count",
        "max_uses",
        "expires_at",
        "is_active",
        "created_at",
    )
    list_filter = ("tenant", "is_active")
    search_fields = ("label", "tenant__name", "code", "code_prefix")
    readonly_fields = (
        "tenant",
        "label",
        "enrollment_code",
        "code_prefix",
        "code_hash",
        "expires_at",
        "max_uses",
        "usage_count",
        "created_by",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    @admin.display(description="Enrollment code", empty_value="Unavailable for legacy code")
    def enrollment_code(self, obj):
        return obj.code or None


@admin.register(TenantStudentInvite)
class TenantStudentInviteAdmin(PlatformSuperuserAdminMixin, admin.ModelAdmin):
    list_display = ("email", "full_name", "tenant", "is_active", "accepted_by", "accepted_at", "created_at")
    list_filter = ("tenant", "is_active", "accepted_at")
    search_fields = ("email", "full_name", "tenant__name")
    readonly_fields = ("accepted_by", "accepted_at", "created_at", "updated_at")
