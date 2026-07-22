from __future__ import annotations

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "MindMetric Admin"
admin.site.site_title = "MindMetric"
admin.site.index_title = "MindMetric Administration"


urlpatterns = [
    path("", include("backend.apps.pages.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("backend.apps.accounts.urls")),
    path("api/billing/", include("backend.apps.billing.urls")),
    path("api/tests/", include("backend.apps.assessments.urls")),
]
