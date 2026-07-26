from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

from backend.apps.tenants.services import is_institution_tenant
from backend.apps.tenants.utils import get_default_tenant


class TenantAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        tenant_return_url = request.session.pop("tenant_oauth_return_url", "")
        if tenant_return_url:
            return tenant_return_url
        return super().get_login_redirect_url(request)


class TenantSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        tenant = getattr(request, "tenant", None)
        if user.tenant_id is None:
            # Institutional access is represented by TenantMembership, not by
            # changing the user's home/platform tenant.
            user.tenant = get_default_tenant() if is_institution_tenant(tenant) else tenant or get_default_tenant()
            user.save(update_fields=["tenant"])
        return user
