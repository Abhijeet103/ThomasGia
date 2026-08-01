from __future__ import annotations

from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from backend.apps.assessments.models import AssessmentTrack, PracticeTrackVisibility
from backend.apps.assessments.services import record_practice_progress
from backend.apps.tenants.models import (
    EnrollmentMode,
    EnrollmentSource,
    Tenant,
    TenantEnrollmentCode,
    TenantMembership,
    TenantStudentInvite,
    TenantType,
    TenantUser,
)
from backend.apps.tenants.utils import reset_current_tenant_slug, set_current_tenant_slug


User = get_user_model()


class TenantAccessFlowTests(TestCase):
    def setUp(self):
        self.platform, _ = Tenant.objects.update_or_create(
            slug="mindmetric",
            defaults={
                "name": "MindMetric",
                "primary_domain": "mindmetric.store",
                "tenant_type": TenantType.PLATFORM,
                "subdomain_prefix": None,
                "allowed_assessments": ["prepgia", "ccat"],
            },
        )
        self.user = User.objects.create_user(email="student@example.com", password="password", tenant=self.platform)

    def create_institution(
        self,
        *,
        prefix="test-academy",
        enrollment_mode=EnrollmentMode.OPEN,
        default_plan_code="weekly",
    ):
        return Tenant.objects.create(
            name=prefix.title(),
            slug=prefix,
            primary_domain=f"{prefix}.mindmetric.store",
            tenant_type=TenantType.INSTITUTION,
            subdomain_prefix=prefix,
            enrollment_mode=enrollment_mode,
            default_plan_code=default_plan_code,
            allowed_assessments=["prepgia"],
        )

    def test_open_tenant_enrolls_once_without_changing_platform_subscription(self):
        tenant = self.create_institution()
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(response.status_code, 200)
        membership = TenantMembership.objects.get(tenant=tenant, user=self.user)
        tenant_user = TenantUser.objects.get(tenant=tenant, identity=self.user)
        original_expiry = membership.access_expires_at
        self.assertEqual(membership.tenant_user, tenant_user)
        self.assertEqual(tenant_user.email, self.user.email)
        self.assertEqual(membership.enrollment_source, EnrollmentSource.OPEN_LOGIN)
        self.assertEqual(self.user.role, "free")
        self.assertIsNone(self.user.subscription_expires_at)
        self.assertEqual(response.wsgi_request.effective_role, "paid")
        self.assertEqual(response.wsgi_request.effective_role_label, "Weekly plan")
        self.assertEqual(response.wsgi_request.effective_plan_code, "weekly")
        self.assertTrue(response.wsgi_request.effective_access_tenant_managed)
        self.assertContains(response, "Weekly plan")

        self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)
        membership.refresh_from_db()
        self.assertEqual(membership.access_expires_at, original_expiry)

    def test_weekly_default_plan_starts_when_member_joins(self):
        tenant = self.create_institution()
        joined_at = timezone.now()
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(response.status_code, 200)
        membership = TenantMembership.objects.get(tenant=tenant, user=self.user)
        self.assertEqual(membership.plan_code, "weekly")
        self.assertGreaterEqual(
            membership.access_expires_at,
            joined_at + timedelta(days=7),
        )
        self.assertLess(
            membership.access_expires_at,
            joined_at + timedelta(days=7, minutes=1),
        )

        session_response = self.client.get(
            "/api/auth/session/",
            HTTP_HOST=tenant.primary_domain,
        )
        self.assertEqual(session_response.status_code, 200)
        session_user = session_response.json()["user"]
        self.assertEqual(session_user["role"], "paid")
        self.assertEqual(session_user["role_label"], "Weekly plan")
        self.assertEqual(session_user["plan_code"], "weekly")
        self.assertTrue(session_user["tenant_managed"])

        subscription_response = self.client.get(
            reverse("pages:subscription"),
            HTTP_HOST=tenant.primary_domain,
        )
        self.assertEqual(subscription_response.status_code, 200)
        self.assertContains(subscription_response, "Weekly plan")
        self.assertContains(subscription_response, f"Access provided by {tenant.name}")
        self.assertNotContains(subscription_response, "Cancel subscription")
        self.assertNotContains(subscription_response, "Need more time?")

    def test_no_default_plan_does_not_grant_automatic_membership(self):
        tenant = self.create_institution(default_plan_code=None)
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertRedirects(
            response,
            f"{reverse('tenants:activate')}?next=/practice/",
            fetch_redirect_response=False,
        )
        self.assertFalse(
            TenantMembership.objects.filter(tenant=tenant, user=self.user).exists()
        )

    def test_code_tenant_redirects_and_redeems_valid_code(self):
        tenant = self.create_institution(enrollment_mode=EnrollmentMode.CODE_REQUIRED)
        raw_code = "MM-TESTCODE"
        enrollment_code = TenantEnrollmentCode.objects.create(
            tenant=tenant,
            label="Cohort A",
            code_prefix="MM-TEST",
            code_hash=TenantEnrollmentCode.hash_code(raw_code),
            max_uses=2,
        )
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)
        self.assertRedirects(
            response,
            f"{reverse('tenants:activate')}?next=/practice/",
            fetch_redirect_response=False,
        )

        invalid = self.client.post(
            reverse("tenants:activate"),
            {"enrollment_code": "WRONG", "next": "/practice/"},
            HTTP_HOST=tenant.primary_domain,
        )
        self.assertEqual(invalid.status_code, 400)

        valid = self.client.post(
            reverse("tenants:activate"),
            {"enrollment_code": raw_code, "next": "/practice/"},
            HTTP_HOST=tenant.primary_domain,
        )
        self.assertRedirects(valid, "/practice/", fetch_redirect_response=False)
        self.assertTrue(TenantMembership.objects.get(tenant=tenant, user=self.user).is_active)
        enrollment_code.refresh_from_db()
        self.assertEqual(enrollment_code.usage_count, 1)

    def test_preadded_student_is_admitted_without_code(self):
        tenant = self.create_institution(enrollment_mode=EnrollmentMode.CODE_REQUIRED)
        invite = TenantStudentInvite.objects.create(tenant=tenant, email=self.user.email.upper())
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(response.status_code, 200)
        membership = TenantMembership.objects.get(tenant=tenant, user=self.user)
        self.assertEqual(membership.enrollment_source, EnrollmentSource.INVITE)
        invite.refresh_from_db()
        self.assertEqual(invite.accepted_by, self.user)
        self.assertIsNotNone(invite.accepted_at)

    def test_platform_domain_does_not_create_institution_membership(self):
        self.client.force_login(self.user)
        response = self.client.get("/practice/", HTTP_HOST=self.platform.primary_domain)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TenantMembership.objects.exists())
        self.assertTrue(TenantUser.objects.filter(tenant=self.platform, identity=self.user).exists())

    def test_same_login_has_distinct_platform_and_institution_user_entries(self):
        tenant = self.create_institution(prefix="demo-profile")
        platform_client = Client()
        tenant_client = Client()
        platform_client.force_login(self.user)
        tenant_client.force_login(self.user)

        platform_response = platform_client.get("/practice/", HTTP_HOST=self.platform.primary_domain)
        tenant_response = tenant_client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(platform_response.status_code, 200)
        self.assertEqual(tenant_response.status_code, 200)
        tenant_users = TenantUser.objects.filter(identity=self.user).order_by("tenant_id")
        self.assertEqual(tenant_users.count(), 2)
        self.assertEqual(set(tenant_users.values_list("tenant_id", flat=True)), {self.platform.id, tenant.id})
        self.assertEqual(set(tenant_users.values_list("email", flat=True)), {self.user.email})

    def test_tenant_progress_is_attached_to_the_active_tenant_user(self):
        tenant = self.create_institution(prefix="demo-progress")
        self.client.force_login(self.user)
        self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)
        tenant_user = TenantUser.objects.get(tenant=tenant, identity=self.user)

        token = set_current_tenant_slug(tenant.slug)
        try:
            progress = record_practice_progress(self.user, "reasoning")
        finally:
            reset_current_tenant_slug(token)

        self.assertEqual(progress.tenant, tenant)
        self.assertEqual(progress.tenant_user, tenant_user)

    def test_platform_tenant_allow_list_hides_unselected_assessments(self):
        self.platform.allowed_assessments = ["prepgia", "ccat"]
        self.platform.save(update_fields=("allowed_assessments", "updated_at"))
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=self.platform.primary_domain)

        self.assertEqual(response.status_code, 200)
        assessment_keys = [card["key"] for card in response.context["assessments"]]
        self.assertEqual(assessment_keys, ["prepgia", "ccat"])

    def test_anonymous_open_practice_link_does_not_require_login(self):
        response = self.client.get(
            reverse("pages:practice"),
            HTTP_HOST=self.platform.primary_domain,
        )

        self.assertEqual(response.status_code, 200)
        prepgia_card = next(
            card
            for card in response.context["assessments"]
            if card["key"] == "prepgia"
        )
        self.assertEqual(
            prepgia_card["open_url"],
            reverse("pages:assessment-practice", args=["prepgia"]),
        )
        self.assertNotIn(reverse("pages:login"), prepgia_card["open_url"])

    def test_unselected_assessment_is_hidden_and_direct_route_is_not_found(self):
        tenant = self.create_institution()
        self.client.force_login(self.user)

        response = self.client.get("/practice/ccat/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(response.status_code, 404)

    def test_selector_hides_every_assessment_not_allowed_by_tenant(self):
        tenant = self.create_institution()
        tenant.allowed_assessments = ["prepgia", "ccat"]
        tenant.save(update_fields=("allowed_assessments", "updated_at"))
        AssessmentTrack.objects.update_or_create(
            tenant=None,
            assessment_type="watson_glaser",
            defaults={
                "title": "Watson-Glaser",
                "visibility_state": PracticeTrackVisibility.UPCOMING,
                "is_active": True,
            },
        )
        AssessmentTrack.objects.update_or_create(
            tenant=tenant,
            assessment_type="shl_verify",
            defaults={
                "title": "SHL Verify",
                "visibility_state": PracticeTrackVisibility.ACCESSIBLE,
                "is_active": True,
            },
        )
        self.client.force_login(self.user)

        response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)

        self.assertEqual(response.status_code, 200)
        assessment_keys = [card["key"] for card in response.context["assessments"]]
        self.assertEqual(assessment_keys, ["prepgia", "ccat"])

    def test_google_login_on_subdomain_uses_the_tenant_callback(self):
        tenant = self.create_institution()

        response = self.client.get(
            "/accounts/google/login/?next=/dashboard/",
            HTTP_HOST=tenant.primary_domain,
            secure=True,
        )

        oauth_url = urlparse(response.url)
        self.assertEqual(oauth_url.netloc, "accounts.google.com")
        self.assertEqual(
            parse_qs(oauth_url.query)["redirect_uri"],
            [f"https://{tenant.primary_domain}/accounts/google/login/callback/"],
        )
        self.assertNotIn("tenant_oauth_return_url", self.client.session)
        self.assertNotIn("tenant_oauth_tenant_id", self.client.session)

    def test_authenticated_session_is_rejected_on_another_tenant(self):
        tenant = self.create_institution(prefix="isolated")
        self.client.force_login(self.user)

        tenant_response = self.client.get("/practice/", HTTP_HOST=tenant.primary_domain)
        platform_response = self.client.get("/practice/", HTTP_HOST=self.platform.primary_domain)

        self.assertEqual(tenant_response.status_code, 200)
        self.assertEqual(platform_response.status_code, 403)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_independent_clients_can_login_on_separate_tenants(self):
        tenant = self.create_institution(prefix="independent")
        platform_client = Client()
        tenant_client = Client()
        platform_client.force_login(self.user)
        tenant_client.force_login(self.user)

        platform_response = platform_client.get(
            "/practice/",
            HTTP_HOST=self.platform.primary_domain,
        )
        tenant_response = tenant_client.get(
            "/practice/",
            HTTP_HOST=tenant.primary_domain,
        )

        self.assertEqual(platform_response.status_code, 200)
        self.assertEqual(tenant_response.status_code, 200)
        self.assertEqual(platform_client.session["_mindmetric_auth_tenant_id"], self.platform.id)
        self.assertEqual(tenant_client.session["_mindmetric_auth_tenant_id"], tenant.id)

    def test_email_login_binds_session_and_rejects_external_next_url(self):
        tenant = self.create_institution(prefix="email-login")

        response = self.client.post(
            "/login/",
            {
                "login": self.user.email,
                "password": "password",
                "next": "https://mindmetric.store/dashboard/",
            },
            HTTP_HOST=tenant.primary_domain,
            secure=True,
        )

        self.assertRedirects(response, "/", fetch_redirect_response=False)
        self.assertEqual(self.client.session["_mindmetric_auth_tenant_id"], tenant.id)
        self.assertEqual(response.cookies[settings.SESSION_COOKIE_NAME]["domain"], "")

    def test_institution_domain_is_derived_from_prefix(self):
        tenant = self.create_institution(prefix="academy")
        self.assertEqual(tenant.primary_domain, "academy.mindmetric.store")


class TenantMembershipExpiryTests(TestCase):
    def test_expired_membership_reports_inactive(self):
        platform, _ = Tenant.objects.update_or_create(
            slug="mindmetric",
            defaults={
                "name": "MindMetric",
                "primary_domain": "mindmetric.store",
                "tenant_type": TenantType.PLATFORM,
                "subdomain_prefix": None,
            },
        )
        tenant = Tenant.objects.create(
            name="Expiry Demo",
            slug="expiry-demo",
            primary_domain="expiry-demo.mindmetric.store",
            tenant_type=TenantType.INSTITUTION,
            subdomain_prefix="expiry-demo",
        )
        user = User.objects.create_user(email="expired@example.com", tenant=platform)
        now = timezone.now()
        membership = TenantMembership.objects.create(
            tenant=tenant,
            user=user,
            plan_code="weekly",
            access_started_at=now,
            access_expires_at=now,
            enrollment_source=EnrollmentSource.ADMIN,
        )
        self.assertFalse(membership.is_active)
