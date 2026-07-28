from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from backend.apps.billing.models import BillingPlan
from backend.apps.billing.services import create_checkout_session, get_plan_definition


User = get_user_model()


class BillingPlanTests(TestCase):
    def test_admin_price_is_used_by_plan_catalog(self):
        plan = BillingPlan.objects.get(code="weekly")
        plan.price = "14.50"
        plan.save(update_fields=("price", "updated_at"))

        definition = get_plan_definition("weekly")

        self.assertEqual(definition.price_display, "$14.50")
        self.assertEqual(definition.price_value, "14.50")

    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_WEBHOOK_SECRET="whsec_test",
    )
    @patch("backend.apps.billing.services.stripe.checkout.Session.create")
    def test_stripe_checkout_uses_admin_price(self, create_session):
        plan = BillingPlan.objects.get(code="monthly")
        plan.price = "24.75"
        plan.save(update_fields=("price", "updated_at"))
        user = User.objects.create_user(email="buyer@example.com", password="secret")
        create_session.return_value = SimpleNamespace(
            id="cs_test",
            url="https://checkout.stripe.test/session",
        )

        checkout_url = create_checkout_session(
            user,
            "monthly",
            base_url="https://mindmetric.store",
        )

        self.assertEqual(checkout_url, "https://checkout.stripe.test/session")
        line_item = create_session.call_args.kwargs["line_items"][0]
        self.assertEqual(line_item["price_data"]["unit_amount"], 2475)
        self.assertEqual(line_item["price_data"]["currency"], "usd")
