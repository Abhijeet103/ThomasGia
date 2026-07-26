from __future__ import annotations

from django import forms
from django.conf import settings
from django.db import transaction

from backend.apps.assessments.config import PRACTICE_TRACK_LIBRARY
from backend.apps.assessments.models import AssessmentTrack, PracticeTrackVisibility

from .models import EnrollmentMode, Tenant, TenantPlan, TenantType


NOT_ALLOCATED = "not_allocated"
ASSESSMENT_STATE_CHOICES = (
    (NOT_ALLOCATED, "Not allocated"),
    (PracticeTrackVisibility.ACCESSIBLE, "Accessible (live)"),
    (PracticeTrackVisibility.UPCOMING, "Upcoming"),
    (PracticeTrackVisibility.HIDDEN, "Hidden"),
)
ASSESSMENT_STATE_FIELD_NAMES = tuple(
    f"assessment_state_{assessment_key}"
    for assessment_key in PRACTICE_TRACK_LIBRARY
)


def _assessment_state_field(assessment_key: str) -> forms.ChoiceField:
    config = PRACTICE_TRACK_LIBRARY[assessment_key]
    return forms.ChoiceField(
        label=config["title"],
        choices=ASSESSMENT_STATE_CHOICES,
        help_text="Not allocated hides access completely. Hidden keeps the assessment allocated but removes it from the frontend.",
    )


class TenantAssessmentStateFormMixin(forms.ModelForm):
    assessment_state_prepgia = _assessment_state_field("prepgia")
    assessment_state_ccat = _assessment_state_field("ccat")
    assessment_state_watson_glaser = _assessment_state_field("watson_glaser")
    assessment_state_shl_verify = _assessment_state_field("shl_verify")

    def _configure_assessment_state_fields(self):
        allowed_assessments = set(getattr(self.instance, "allowed_assessments", None) or [])
        tracks_by_key = {}
        if getattr(self.instance, "pk", None):
            tracks_by_key = {
                track.assessment_type: track
                for track in AssessmentTrack.objects.filter(tenant=self.instance)
            }

        for assessment_key, config in PRACTICE_TRACK_LIBRARY.items():
            track = tracks_by_key.get(assessment_key)
            if assessment_key not in allowed_assessments:
                initial = NOT_ALLOCATED
            elif track:
                initial = track.visibility_state
            else:
                initial = config.get(
                    "default_visibility_state",
                    PracticeTrackVisibility.ACCESSIBLE,
                )
            self.fields[f"assessment_state_{assessment_key}"].initial = initial

    def assessment_states(self) -> dict[str, str]:
        return {
            assessment_key: self.cleaned_data[f"assessment_state_{assessment_key}"]
            for assessment_key in PRACTICE_TRACK_LIBRARY
        }

    def _set_allowed_assessments(self, tenant: Tenant) -> None:
        tenant.allowed_assessments = [
            assessment_key
            for assessment_key, state in self.assessment_states().items()
            if state != NOT_ALLOCATED
        ]

    @transaction.atomic
    def sync_assessment_tracks(self, tenant: Tenant) -> None:
        states = self.assessment_states()
        allowed_assessments = [
            assessment_key
            for assessment_key, state in states.items()
            if state != NOT_ALLOCATED
        ]
        if tenant.allowed_assessments != allowed_assessments:
            tenant.allowed_assessments = allowed_assessments
            tenant.save(update_fields=("allowed_assessments", "updated_at"))

        for assessment_key, config in PRACTICE_TRACK_LIBRARY.items():
            state = states[assessment_key]
            is_allocated = state != NOT_ALLOCATED
            visibility_state = state if is_allocated else PracticeTrackVisibility.HIDDEN
            track, _ = AssessmentTrack.objects.get_or_create(
                tenant=tenant,
                assessment_type=assessment_key,
                defaults={
                    "title": config["title"],
                    "description": config["description"],
                    "module_count": config["module_count"],
                    "trust_line": config.get("trust_line", ""),
                    "available_languages": config.get("available_languages", []),
                    "visibility_state": visibility_state,
                    "is_active": is_allocated,
                },
            )
            update_fields = []
            if track.visibility_state != visibility_state:
                track.visibility_state = visibility_state
                update_fields.append("visibility_state")
            if track.is_active != is_allocated:
                track.is_active = is_allocated
                update_fields.append("is_active")
            if update_fields:
                track.save(update_fields=(*update_fields, "updated_at"))


class TenantCreateForm(TenantAssessmentStateFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_assessment_state_fields()
        self.fields["default_plan_code"].choices = [
            ("", "No automatic plan"),
            *TenantPlan.choices,
        ]
        if not self.is_bound:
            self.fields["assessment_state_prepgia"].initial = PracticeTrackVisibility.ACCESSIBLE

    class Meta:
        model = Tenant
        fields = (
            "name",
            "slug",
            "subdomain_prefix",
            "enrollment_mode",
            "default_plan_code",
            "is_active",
        )

    def save(self, commit=True):
        tenant = super().save(commit=False)
        tenant.tenant_type = TenantType.INSTITUTION
        tenant.primary_domain = f"{tenant.subdomain_prefix}.{settings.TENANT_BASE_DOMAIN}"
        tenant.default_plan_code = self.cleaned_data.get("default_plan_code") or None
        self._set_allowed_assessments(tenant)
        if commit:
            tenant.save()
            self.sync_assessment_tracks(tenant)
        return tenant


class TenantAdminForm(TenantAssessmentStateFormMixin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._configure_assessment_state_fields()
        self.fields["default_plan_code"].choices = [
            ("", "No automatic plan"),
            *TenantPlan.choices,
        ]

    class Meta:
        model = Tenant
        fields = "__all__"
        exclude = ("allowed_assessments",)

    def save(self, commit=True):
        tenant = super().save(commit=False)
        tenant.default_plan_code = self.cleaned_data.get("default_plan_code") or None
        self._set_allowed_assessments(tenant)
        if commit:
            tenant.save()
            self.sync_assessment_tracks(tenant)
        return tenant


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


class EnrollmentCodeGenerateForm(forms.Form):
    label = forms.CharField(max_length=120, required=False)
    max_uses = forms.IntegerField(min_value=1, initial=1)
    expires_at = forms.DateTimeField(required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))


class StudentInviteBulkForm(forms.Form):
    students = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 12}),
        help_text="One student per line. Use email@example.com or email@example.com, Full Name.",
    )

    def clean_students(self):
        rows = []
        seen = set()
        for line_number, raw_line in enumerate(self.cleaned_data["students"].splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            email, separator, full_name = line.partition(",")
            email = email.strip().lower()
            try:
                forms.EmailField().clean(email)
            except forms.ValidationError as exc:
                raise forms.ValidationError(f"Line {line_number} has an invalid email address.") from exc
            if email not in seen:
                rows.append((email, full_name.strip() if separator else ""))
                seen.add(email)
        if not rows:
            raise forms.ValidationError("Add at least one student email.")
        return rows
