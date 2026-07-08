from django.urls import path

from .views import BillingStatusView, CancelSubscriptionView, StartCheckoutView, StripeWebhookView


urlpatterns = [
    path("status/", BillingStatusView.as_view(), name="billing-status"),
    path("checkout/<slug:plan_code>/", StartCheckoutView.as_view(), name="billing-checkout"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="billing-stripe-webhook"),
    path("cancel/", CancelSubscriptionView.as_view(), name="billing-cancel"),
]
