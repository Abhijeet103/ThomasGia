from __future__ import annotations

from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from backend.apps.pages.seo import canonical_site_url
from backend.apps.pages.sitemaps import PublicPageSitemap

admin.site.site_header = "MindMetric Admin"
admin.site.site_title = "MindMetric"
admin.site.index_title = "MindMetric Administration"


urlpatterns = [
    path(
        "robots.txt",
        TemplateView.as_view(
            template_name="robots.txt",
            content_type="text/plain",
            extra_context={"site_url": canonical_site_url()},
        ),
        name="robots",
    ),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": {"public": PublicPageSitemap}},
        name="sitemap",
    ),
    path("", include("backend.apps.pages.urls")),
    path("admin/", admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("api/auth/", include("backend.apps.accounts.urls")),
    path("api/billing/", include("backend.apps.billing.urls")),
    path("api/tests/", include("backend.apps.assessments.urls")),
    path("tenant-access/", include("backend.apps.tenants.urls")),
]
