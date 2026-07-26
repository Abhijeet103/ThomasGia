from django import forms

from backend.apps.tenants.services import is_institution_tenant
from backend.apps.tenants.utils import get_default_tenant


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="Name", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        request_tenant = getattr(request, "tenant", None)
        if is_institution_tenant(request_tenant):
            request_tenant = None
        user.tenant = request_tenant or user.tenant or get_default_tenant()
        user.save(update_fields=["first_name", "tenant"])
