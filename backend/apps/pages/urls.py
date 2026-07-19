from django.urls import path

from .views import (
    AssessmentPracticePageView,
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
    path("pricing/", PricingPageView.as_view(), name="pricing"),
    path("practice/", PracticePageView.as_view(), name="practice"),
    path("practice/<slug:assessment_slug>/", AssessmentPracticePageView.as_view(), name="assessment-practice"),
    path("practice/<slug:assessment_slug>/full-test/", FullTestPageView.as_view(), name="assessment-full-test"),
    path("practice/<slug:assessment_slug>/modules/<slug:slug>/", SectionDetailPageView.as_view(), name="assessment-section-detail"),
    path("full-test/", FullTestPageView.as_view(), {"assessment_slug": "prepgia"}, name="full-test"),
    path("subscription/", SubscriptionPageView.as_view(), name="subscription"),
    path("sections/", SectionsPageView.as_view(), name="sections"),
    path("sections/<slug:slug>/", SectionDetailPageView.as_view(), {"assessment_slug": "prepgia"}, name="section-detail"),
    path("login/", LoginPageView.as_view(), name="login"),
    path("dashboard/", DashboardPageView.as_view(), name="dashboard"),
]
