from __future__ import annotations

from django import forms

from .models import Tenant


class TenantCreateForm(forms.ModelForm):
    class Meta:
        model = Tenant
        fields = ("name", "slug", "primary_domain", "is_active")


class TenantAdminUserCreateForm(forms.Form):
    email = forms.EmailField()
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("password1") != cleaned_data.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

