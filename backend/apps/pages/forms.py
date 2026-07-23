from django import forms

from .models import SaleInquiry, TestSuggestion


class SaleInquiryForm(forms.ModelForm):
    next = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = SaleInquiry
        fields = ("email", "phone", "message", "source_page")
        widgets = {
            "source_page": forms.HiddenInput(),
            "message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"next", "source_page"}:
                continue
            field.widget.attrs.setdefault("class", "form-input")
        self.fields["email"].widget.attrs.setdefault("placeholder", "you@company.com")
        self.fields["phone"].widget.attrs.setdefault("placeholder", "Phone number")
        self.fields["message"].widget.attrs.setdefault("placeholder", "Ask anything")


class TrackWaitlistForm(forms.Form):
    assessment_type = forms.CharField(max_length=64, widget=forms.HiddenInput())
    next = forms.CharField(widget=forms.HiddenInput(), required=False)


class TestSuggestionForm(forms.ModelForm):
    next = forms.CharField(widget=forms.HiddenInput(), required=False)

    class Meta:
        model = TestSuggestion
        fields = ("email", "requested_test", "message", "source_page")
        widgets = {
            "source_page": forms.HiddenInput(),
            "message": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in {"next", "source_page"}:
                continue
            field.widget.attrs.setdefault("class", "form-input")
        self.fields["email"].widget.attrs.setdefault("placeholder", "you@example.com")
        self.fields["requested_test"].widget.attrs.setdefault("placeholder", "e.g. Watson-Glaser, SHL Verify, Raven's Progressive Matrices")
        self.fields["message"].widget.attrs.setdefault("placeholder", "Anything specific you want in this test?")
