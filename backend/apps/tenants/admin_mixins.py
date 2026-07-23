from __future__ import annotations

from django.contrib import admin


class TenantScopedAdminMixin(admin.ModelAdmin):
    tenant_field_name = "tenant"

    def _has_platform_access(self, request) -> bool:
        return bool(request.user.is_superuser)

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if self._has_platform_access(request):
            return queryset
        tenant = getattr(request.user, "tenant", None)
        if tenant is None:
            return queryset.none()
        return queryset.filter(**{self.tenant_field_name: tenant})

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not self._has_platform_access(request) and db_field.name == self.tenant_field_name:
            tenant = getattr(request.user, "tenant", None)
            if tenant is not None:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(id=tenant.id)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not self._has_platform_access(request) and hasattr(obj, self.tenant_field_name):
            setattr(obj, self.tenant_field_name, getattr(request.user, "tenant", None))
        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        allowed = super().has_view_permission(request, obj=obj)
        if not allowed or obj is None or self._has_platform_access(request):
            return allowed
        return getattr(obj, self.tenant_field_name + "_id", None) == getattr(request.user, "tenant_id", None)

    def has_change_permission(self, request, obj=None):
        allowed = super().has_change_permission(request, obj=obj)
        if not allowed or obj is None or self._has_platform_access(request):
            return allowed
        return getattr(obj, self.tenant_field_name + "_id", None) == getattr(request.user, "tenant_id", None)

    def has_delete_permission(self, request, obj=None):
        allowed = super().has_delete_permission(request, obj=obj)
        if not allowed or obj is None or self._has_platform_access(request):
            return allowed
        return getattr(obj, self.tenant_field_name + "_id", None) == getattr(request.user, "tenant_id", None)

