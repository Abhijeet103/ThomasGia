from django import forms


class CustomSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="Name", required=True)

    def signup(self, request, user):
        user.first_name = self.cleaned_data["first_name"]
        user.save(update_fields=["first_name"])
