from __future__ import annotations

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse

from .forms import TenantAdminUserCreateForm, TenantCreateForm
from .models import Tenant

User = get_user_model()


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "primary_domain", "is_active", "updated_at")
    search_fields = ("name", "slug", "primary_domain")
    list_filter = ("is_active",)
    change_list_template = "admin/tenants/tenant/change_list.html"
    change_form_template = "admin/tenants/tenant/change_form.html"

    def get_urls(self):
        custom_urls = [
            path(
                "create/",
                self.admin_site.admin_view(self.create_tenant_view),
                name="tenants_tenant_create",
            ),
            path(
                "<path:object_id>/create-admin/",
                self.admin_site.admin_view(self.create_tenant_admin_view),
                name="tenants_tenant_create_admin",
            ),
        ]
        return custom_urls + super().get_urls()

    def create_tenant_view(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_superuser:
            self.message_user(request, "Only platform superusers can create tenants.", level=messages.ERROR)
            return redirect("admin:tenants_tenant_changelist")

        if request.method == "POST":
            form = TenantCreateForm(request.POST)
            if form.is_valid():
                tenant = form.save()
                self.message_user(request, f"Created tenant {tenant.name}.", level=messages.SUCCESS)
                return redirect(reverse("admin:tenants_tenant_change", args=[tenant.pk]))
        else:
            form = TenantCreateForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "title": "Create tenant",
            "form": form,
        }
        return render(request, "admin/tenants/tenant/create_tenant.html", context)

    def create_tenant_admin_view(self, request: HttpRequest, object_id: str) -> HttpResponse:
        if not request.user.is_superuser:
            self.message_user(request, "Only platform superusers can create tenant admins.", level=messages.ERROR)
            return redirect("admin:tenants_tenant_changelist")

        tenant = get_object_or_404(Tenant, pk=object_id)
        if request.method == "POST":
            form = TenantAdminUserCreateForm(request.POST)
            if form.is_valid():
                user = User.objects.create_user(
                    email=form.cleaned_data["email"],
                    password=form.cleaned_data["password1"],
                    first_name=form.cleaned_data.get("first_name", ""),
                    last_name=form.cleaned_data.get("last_name", ""),
                )
                user.tenant = tenant
                user.is_staff = True
                user.is_tenant_admin = True
                user.is_superuser = False
                user.save(update_fields=["tenant", "is_staff", "is_tenant_admin", "is_superuser"])
                self.message_user(
                    request,
                    f"Created tenant admin {user.email} for {tenant.name}.",
                    level=messages.SUCCESS,
                )
                return redirect(reverse("admin:accounts_user_change", args=[user.pk]))
        else:
            form = TenantAdminUserCreateForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "original": tenant,
            "tenant": tenant,
            "title": f"Create tenant admin for {tenant.name}",
            "form": form,
        }
        return render(request, "admin/tenants/tenant/create_tenant_admin.html", context)

    def render_change_form(self, request, context, *args, **kwargs):
        obj = context.get("original")
        context["tenant_admin_create_url"] = (
            reverse("admin:tenants_tenant_create_admin", args=[obj.pk]) if obj and request.user.is_superuser else ""
        )
        return super().render_change_form(request, context, *args, **kwargs)
