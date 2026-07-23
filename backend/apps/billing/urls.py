from django.urls import path

from .views import (
    BillingStatusView,
    CancelSubscriptionView,
    PayPalReturnView,
    PayPalWebhookView,
    StartCheckoutView,
    StartPayPalCheckoutView,
    StripeWebhookView,
)


urlpatterns = [
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("checkout/<slug:plan_code>/", StartCheckoutView.as_view(), name="billing-checkout"),
    path("checkout/paypal/<slug:plan_code>/", StartPayPalCheckoutView.as_view(), name="billing-paypal-checkout"),
    path("paypal/return/", PayPalReturnView.as_view(), name="billing-paypal-return"),
    path("paypal/webhook/", PayPalWebhookView.as_view(), name="billing-paypal-webhook"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
    path("cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
]
