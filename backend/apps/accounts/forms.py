from django import forms

from backend.apps.tenants.utils import get_default_tenant


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="Name", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.tenant = getattr(request, "tenant", None) or user.tenant or get_default_tenant()
        user.save(update_fields=["first_name", "tenant"])
