from django.urls import path

from .views import (
    DashboardPageView,
    FullTestPageView,
    HomePageView,
    LoginPageView,
    PracticePageView,
    PricingPageView,
    SectionDetailPageView,
    SectionsPageView,
    SubscriptionPageView,
)


app_name = "pages"

urlpatterns = [
    path("", HomePageView.as_view(), name="home"),
    path("full-test/", FullTestPageView.as_view(), name="full-test"),
    path("pricing/", PricingPageView.as_view(), name="pricing"),
    path("practice/", PracticePageView.as_view(), name="practice"),
    path("subscription/", SubscriptionPageView.as_view(), name="subscription"),
    path("sections/", SectionsPageView.as_view(), name="sections"),
    path("sections/<slug:slug>/", SectionDetailPageView.as_view(), name="section-detail"),
    path("login/", LoginPageView.as_view(), name="login"),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard"),
]
