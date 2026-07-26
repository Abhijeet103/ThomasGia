from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from backend.apps.assessments.models import AssessmentTrack, PracticeTrackVisibility
from backend.apps.tenants.admin import TenantAdmin
from backend.apps.tenants.forms import TenantAdminForm
from backend.apps.tenants.models import Tenant, TenantType


User = get_user_model()


class TenantAssessmentAdminFormTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Admin Test",
            slug="admin-test",
            primary_domain="admin-test.mindmetric.store",
            tenant_type=TenantType.INSTITUTION,
            subdomain_prefix="admin-test",
            allowed_assessments=["prepgia", "ccat"],
        )
        AssessmentTrack.objects.create(
            tenant=self.tenant,
            assessment_type="prepgia",
            title="Thomas GIA",
            visibility_state=PracticeTrackVisibility.ACCESSIBLE,
        )
        AssessmentTrack.objects.create(
            tenant=self.tenant,
            assessment_type="ccat",
            title="CCAT",
            visibility_state=PracticeTrackVisibility.UPCOMING,
        )
        self.superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="password",
        )

    def test_initial_states_combine_allocation_and_track_visibility(self):
        form = TenantAdminForm(instance=self.tenant)

        self.assertEqual(
            form.fields["assessment_state_prepgia"].initial,
            PracticeTrackVisibility.ACCESSIBLE,
        )
        self.assertEqual(
            form.fields["assessment_state_ccat"].initial,
            PracticeTrackVisibility.UPCOMING,
        )
        self.assertEqual(
            form.fields["assessment_state_watson_glaser"].initial,
            "not_allocated",
        )

    def test_tenant_admin_builds_change_form_with_assessment_fields(self):
        request = RequestFactory().get(
            f"/admin/tenants/tenant/{self.tenant.pk}/change/"
        )
        request.user = self.superuser

        form_class = TenantAdmin(Tenant, admin.site).get_form(
            request,
            obj=self.tenant,
        )

        self.assertIn("assessment_state_prepgia", form_class.base_fields)
        self.assertIn("assessment_state_ccat", form_class.base_fields)
        self.assertIn("assessment_state_watson_glaser", form_class.base_fields)
        self.assertIn("assessment_state_shl_verify", form_class.base_fields)

    def test_tenant_admin_save_synchronizes_allocation_and_visibility(self):
        form = TenantAdminForm(
            data={
                "name": self.tenant.name,
                "slug": self.tenant.slug,
                "primary_domain": self.tenant.primary_domain,
                "tenant_type": self.tenant.tenant_type,
                "subdomain_prefix": self.tenant.subdomain_prefix,
                "enrollment_mode": self.tenant.enrollment_mode,
                "default_plan_code": self.tenant.default_plan_code,
                "is_active": "on",
                "assessment_state_prepgia": PracticeTrackVisibility.ACCESSIBLE,
                "assessment_state_ccat": PracticeTrackVisibility.ACCESSIBLE,
                "assessment_state_watson_glaser": "not_allocated",
                "assessment_state_shl_verify": PracticeTrackVisibility.HIDDEN,
            },
            instance=self.tenant,
        )
        self.assertTrue(form.is_valid(), form.errors)

        tenant = form.save(commit=False)
        request = RequestFactory().post("/admin/tenants/tenant/")
        request.user = self.superuser
        TenantAdmin(Tenant, admin.site).save_model(request, tenant, form, change=True)

        tenant.refresh_from_db()
        self.assertEqual(
            tenant.allowed_assessments,
            ["prepgia", "ccat", "shl_verify"],
        )
        states = {
            track.assessment_type: (track.visibility_state, track.is_active)
            for track in AssessmentTrack.objects.filter(tenant=tenant)
        }
        self.assertEqual(
            states["prepgia"],
            (PracticeTrackVisibility.ACCESSIBLE, True),
        )
        self.assertEqual(
            states["ccat"],
            (PracticeTrackVisibility.ACCESSIBLE, True),
        )
        self.assertEqual(
            states["watson_glaser"],
            (PracticeTrackVisibility.HIDDEN, False),
        )
        self.assertEqual(
            states["shl_verify"],
            (PracticeTrackVisibility.HIDDEN, True),
        )
