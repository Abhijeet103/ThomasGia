from __future__ import annotations

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class TenantSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form=form)
        tenant = getattr(request, "tenant", None)
        if tenant is not None and user.tenant_id is None:
            user.tenant = tenant
            user.save(update_fields=["tenant"])
        return user

