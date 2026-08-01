from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.urls import reverse

from backend.apps.billing.models import BillingPlan, BillingPlanCountryPrice
from backend.apps.billing.regions import get_request_country_code, pricing_region_for_country
from backend.apps.billing.services import (
    build_plan_cards,
    create_checkout_session,
    create_paypal_order,
    get_plan_definition,
)


User = get_user_model()


class BillingPlanTests(TestCase):
    def test_regional_price_overrides_global_plan_price(self):
        regional_price = BillingPlanCountryPrice.objects.get(
            plan__code="weekly",
            country_code="IN",
        )
        regional_price.price = Decimal("749.00")
        regional_price.sale_price = Decimal("599.00")
        regional_price.save(update_fields=("price", "sale_price", "updated_at"))

        definition = get_plan_definition("weekly", country_code="IN")

        self.assertEqual(definition.currency, "INR")
        self.assertEqual(definition.price_display, "₹599.00")
        self.assertEqual(definition.regular_price_display, "₹749.00")
        self.assertEqual(definition.country_code, "IN")
        self.assertEqual(definition.pricing_region, "IN")

    def test_exact_country_override_takes_priority_over_europe_price(self):
        plan = BillingPlan.objects.get(code="monthly")
        BillingPlanCountryPrice.objects.create(
            plan=plan,
            country_code="DE",
            currency="EUR",
            price=Decimal("17.25"),
        )

        definition = get_plan_definition("monthly", country_code="DE")

        self.assertEqual(definition.price_display, "€17.25")
        self.assertEqual(definition.pricing_region, "DE")

    def test_rest_of_world_uses_global_usd_plan(self):
        plan = BillingPlan.objects.get(code="weekly")
        plan.price = Decimal("11.25")
        plan.save(update_fields=("price", "updated_at"))

        definition = get_plan_definition("weekly", country_code="AU")

        self.assertEqual(definition.currency, "USD")
        self.assertEqual(definition.price_display, "$11.25")
        self.assertEqual(definition.pricing_region, "US")

    @override_settings(BILLING_TRUST_PROXY_COUNTRY_HEADERS=True)
    def test_pricing_page_uses_proxy_country_header(self):
        regional_price = BillingPlanCountryPrice.objects.get(
            plan__code="weekly",
            country_code="GB",
        )
        regional_price.price = Decimal("6.75")
        regional_price.save(update_fields=("price", "updated_at"))

        response = self.client.get(
            "/pricing/",
            HTTP_HOST="mindmetric.store",
            HTTP_CF_IPCOUNTRY="GB",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "£6.75")
        self.assertEqual(self.client.session["billing_country_code"], "GB")

    @override_settings(BILLING_TRUST_PROXY_COUNTRY_HEADERS=True)
    def test_country_detection_is_saved_in_session(self):
        response = self.client.get(
            "/pricing/",
            HTTP_HOST="mindmetric.store",
            HTTP_CLOUDFRONT_VIEWER_COUNTRY="IN",
        )
        self.assertEqual(response.status_code, 200)

        request = response.wsgi_request
        self.assertEqual(get_request_country_code(request), "IN")
        self.assertEqual(pricing_region_for_country("FR"), "EU")
        self.assertEqual(pricing_region_for_country("US"), "US")

    def test_admin_price_is_used_by_plan_catalog(self):
        plan = BillingPlan.objects.get(code="weekly")
        plan.price = "14.50"
        plan.save(update_fields=("price", "updated_at"))

        definition = get_plan_definition("weekly")

        self.assertEqual(definition.price_display, "$14.50")
        self.assertEqual(definition.price_value, "14.50")

    def test_sale_price_becomes_effective_price_and_exposes_discount(self):
        plan = BillingPlan.objects.get(code="monthly")
        plan.price = Decimal("19.99")
        plan.sale_price = Decimal("14.99")
        plan.save(update_fields=("price", "sale_price", "updated_at"))

        definition = get_plan_definition("monthly")
        card = next(
            item
            for item in build_plan_cards(None, None)
            if item["code"] == "monthly"
        )

        self.assertEqual(definition.regular_price_display, "$19.99")
        self.assertEqual(definition.price_display, "$14.99")
        self.assertEqual(definition.price_value, "14.99")
        self.assertTrue(definition.has_discount)
        self.assertEqual(definition.discount_percent, 25)
        self.assertEqual(card["regular_price_display"], "$19.99")
        self.assertEqual(card["price_display"], "$14.99")
        self.assertEqual(card["discount_percent"], 25)

    def test_sale_price_cannot_exceed_regular_price(self):
        plan = BillingPlan.objects.get(code="weekly")
        plan.sale_price = plan.price + Decimal("1.00")

        with self.assertRaises(ValidationError):
            plan.full_clean()

    def test_pricing_page_renders_sale_and_regular_prices(self):
        plan = BillingPlan.objects.get(code="monthly")
        plan.price = Decimal("19.99")
        plan.sale_price = Decimal("14.99")
        plan.save(update_fields=("price", "sale_price", "updated_at"))

        response = self.client.get("/pricing/", HTTP_HOST="mindmetric.store")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "$19.99")
        self.assertContains(response, "$14.99")
        self.assertContains(response, "Save 25%")

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

    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_WEBHOOK_SECRET="whsec_test",
    )
    @patch("backend.apps.billing.services.stripe.checkout.Session.create")
    def test_stripe_checkout_charges_sale_price(self, create_session):
        plan = BillingPlan.objects.get(code="monthly")
        plan.sale_price = Decimal("12.25")
        plan.save(update_fields=("sale_price", "updated_at"))
        user = User.objects.create_user(
            email="stripe-sale@example.com",
            password="secret",
        )
        create_session.return_value = SimpleNamespace(
            id="cs_sale",
            url="https://checkout.stripe.test/sale",
        )

        create_checkout_session(
            user,
            "monthly",
            base_url="https://mindmetric.store",
        )

        line_item = create_session.call_args.kwargs["line_items"][0]
        self.assertEqual(line_item["price_data"]["unit_amount"], 1225)

    @override_settings(
        STRIPE_SECRET_KEY="sk_test",
        STRIPE_WEBHOOK_SECRET="whsec_test",
    )
    @patch("backend.apps.billing.services.stripe.checkout.Session.create")
    def test_stripe_checkout_charges_regional_currency_and_price(self, create_session):
        regional_price = BillingPlanCountryPrice.objects.get(
            plan__code="monthly",
            country_code="GB",
        )
        regional_price.price = Decimal("15.50")
        regional_price.save(update_fields=("price", "updated_at"))
        user = User.objects.create_user(
            email="regional-stripe@example.com",
            password="secret",
        )
        create_session.return_value = SimpleNamespace(
            id="cs_regional",
            url="https://checkout.stripe.test/regional",
        )

        create_checkout_session(
            user,
            "monthly",
            base_url="https://mindmetric.store",
            country_code="GB",
        )

        checkout_payload = create_session.call_args.kwargs
        price_data = checkout_payload["line_items"][0]["price_data"]
        self.assertEqual(price_data["unit_amount"], 1550)
        self.assertEqual(price_data["currency"], "gbp")
        self.assertEqual(checkout_payload["metadata"]["country_code"], "GB")
        self.assertEqual(checkout_payload["metadata"]["pricing_region"], "GB")

    @override_settings(
        PAYPAL_CLIENT_ID="paypal-client",
        PAYPAL_CLIENT_SECRET="paypal-secret",
    )
    @patch("backend.apps.billing.services._paypal_request")
    def test_paypal_checkout_charges_sale_price(self, paypal_request):
        plan = BillingPlan.objects.get(code="weekly")
        plan.sale_price = Decimal("7.50")
        plan.save(update_fields=("sale_price", "updated_at"))
        user = User.objects.create_user(
            email="paypal-sale@example.com",
            password="secret",
        )
        paypal_request.return_value = {
            "links": [
                {
                    "rel": "approve",
                    "href": "https://paypal.test/approve",
                }
            ]
        }

        approval_url = create_paypal_order(
            user,
            "weekly",
            base_url="https://mindmetric.store",
        )

        self.assertEqual(approval_url, "https://paypal.test/approve")
        payload = paypal_request.call_args.args[2]
        self.assertEqual(
            payload["purchase_units"][0]["amount"]["value"],
            "7.50",
        )

    def test_admin_action_applies_percentage_discount(self):
        admin_user = User.objects.create_superuser(
            email="billing-admin@example.com",
            password="secret",
        )
        self.client.force_login(admin_user)
        weekly = BillingPlan.objects.get(code="weekly")
        monthly = BillingPlan.objects.get(code="monthly")
        changelist_url = reverse("admin:billing_billingplan_changelist")
        selected_ids = [str(weekly.pk), str(monthly.pk)]

        intermediate = self.client.post(
            changelist_url,
            {
                "action": "apply_percentage_discount",
                "_selected_action": selected_ids,
            },
        )

        self.assertEqual(intermediate.status_code, 200)
        self.assertContains(intermediate, "Discount percentage")

        applied = self.client.post(
            changelist_url,
            {
                "action": "apply_percentage_discount",
                "_selected_action": selected_ids,
                "percentage": "30",
                "confirm_discount": "Apply discount",
            },
        )

        self.assertEqual(applied.status_code, 302)
        weekly.refresh_from_db()
        monthly.refresh_from_db()
        self.assertEqual(weekly.sale_price, Decimal("6.99"))
        self.assertEqual(monthly.sale_price, Decimal("13.99"))

    def test_admin_discount_action_rejects_more_than_ninety_percent(self):
        admin_user = User.objects.create_superuser(
            email="discount-limit@example.com",
            password="secret",
        )
        self.client.force_login(admin_user)
        weekly = BillingPlan.objects.get(code="weekly")

        response = self.client.post(
            reverse("admin:billing_billingplan_changelist"),
            {
                "action": "apply_percentage_discount",
                "_selected_action": [str(weekly.pk)],
                "percentage": "91",
                "confirm_discount": "Apply discount",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Ensure this value is less than or equal to 90",
        )
        weekly.refresh_from_db()
        self.assertIsNone(weekly.sale_price)

    def test_admin_action_clears_sale_discount(self):
        admin_user = User.objects.create_superuser(
            email="clear-discount@example.com",
            password="secret",
        )
        self.client.force_login(admin_user)
        weekly = BillingPlan.objects.get(code="weekly")
        weekly.sale_price = Decimal("5.00")
        weekly.save(update_fields=("sale_price", "updated_at"))

        response = self.client.post(
            reverse("admin:billing_billingplan_changelist"),
            {
                "action": "clear_sale_discount",
                "_selected_action": [str(weekly.pk)],
            },
        )

        self.assertEqual(response.status_code, 302)
        weekly.refresh_from_db()
        self.assertIsNone(weekly.sale_price)
