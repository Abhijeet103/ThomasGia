import json
from types import SimpleNamespace

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from backend.apps.pages.seo import (
    assessment_seo_metadata,
    module_seo_metadata,
    seo_context,
)
from backend.apps.pages.sitemaps import PublicPageSitemap


@override_settings(
    SITE_URL="https://www.mindmetric.store",
    CONTACT_EMAIL="support@mindmetric.store",
    GOOGLE_SITE_VERIFICATION="verification-token",
    THOMAS_GIA_BLOG_URL="https://medium.com/@mindmetric/thomas-gia-guide",
)
class SeoContextTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def make_request(self, path):
        request = self.factory.get(path)
        request.resolver_match = resolve(request.path)
        return request

    def test_public_page_is_indexable_with_apex_canonical(self):
        context = seo_context(
            self.make_request(
                "/practice/prepgia/modules/reasoning/?mode=practice"
            )
        )

        self.assertEqual(
            context["seo_canonical_url"],
            "https://mindmetric.store/practice/prepgia/modules/reasoning/",
        )
        self.assertEqual(context["seo_robots_content"], "index,follow")
        self.assertEqual(
            context["google_site_verification"], "verification-token"
        )
        self.assertEqual(
            context["thomas_gia_blog_url"],
            "https://medium.com/@mindmetric/thomas-gia-guide",
        )

    def test_full_test_is_not_indexable(self):
        context = seo_context(
            self.make_request("/practice/prepgia/full-test/")
        )

        self.assertEqual(context["seo_robots_content"], "noindex,nofollow")

    def test_schema_is_valid_json(self):
        context = seo_context(self.make_request("/"))
        schema = json.loads(context["seo_schema_json"])
        schema_types = {item["@type"] for item in schema["@graph"]}

        self.assertEqual(schema["@context"], "https://schema.org")
        self.assertIn("Organization", schema_types)
        self.assertIn("WebSite", schema_types)
        self.assertIn("WebApplication", schema_types)

    def test_assessment_page_has_breadcrumb_schema(self):
        context = seo_context(self.make_request("/practice/prepgia/"))
        schema = json.loads(context["seo_schema_json"])
        breadcrumb = next(
            item
            for item in schema["@graph"]
            if item["@type"] == "BreadcrumbList"
        )

        self.assertEqual(
            breadcrumb["itemListElement"][-1]["name"],
            "Thomas GIA Practice Test",
        )

    def test_module_page_has_breadcrumb_schema(self):
        context = seo_context(
            self.make_request("/practice/prepgia/modules/reasoning/")
        )
        schema = json.loads(context["seo_schema_json"])
        breadcrumb = next(
            item
            for item in schema["@graph"]
            if item["@type"] == "BreadcrumbList"
        )

        self.assertEqual(len(breadcrumb["itemListElement"]), 3)
        self.assertIn(
            "Thomas GIA Reasoning Practice Test",
            breadcrumb["itemListElement"][-1]["name"],
        )

    def test_social_metadata_uses_absolute_image_url(self):
        context = seo_context(self.make_request("/"))

        self.assertEqual(
            context["seo_social_image_url"],
            (
                "https://mindmetric.store/static/favicons/"
                "android-chrome-512x512.png"
            ),
        )

    @override_settings(
        STORAGES={
            "default": {
                "BACKEND": "django.core.files.storage.FileSystemStorage",
            },
            "staticfiles": {
                "BACKEND": (
                    "django.contrib.staticfiles.storage.StaticFilesStorage"
                ),
            },
        }
    )
    def test_homepage_exposes_complete_favicon_family(self):
        context = seo_context(self.make_request("/"))
        html = render_to_string("base.html", context, request=self.make_request("/"))

        self.assertIn('sizes="48x48"', html)
        self.assertIn("favicons/favicon.svg", html)
        self.assertIn("favicons/favicon.ico", html)
        self.assertIn("favicons/apple-touch-icon.png", html)
        self.assertIn("favicons/site.webmanifest", html)

    @override_settings(
        IS_PRODUCTION=True,
        GOOGLE_ANALYTICS_MEASUREMENT_ID="G-TEST1234",
    )
    def test_google_analytics_is_exposed_in_production(self):
        request = self.make_request("/")
        request.tenant = SimpleNamespace(slug="demo")

        context = seo_context(request)

        self.assertEqual(context["google_analytics_measurement_id"], "G-TEST1234")
        self.assertEqual(context["google_analytics_tenant_slug"], "demo")

    @override_settings(
        IS_PRODUCTION=False,
        GOOGLE_ANALYTICS_MEASUREMENT_ID="G-TEST1234",
    )
    def test_google_analytics_is_disabled_outside_production(self):
        context = seo_context(self.make_request("/"))

        self.assertEqual(context["google_analytics_measurement_id"], "")

    @override_settings(
        IS_PRODUCTION=True,
        GOOGLE_ANALYTICS_MEASUREMENT_ID="invalid-id",
    )
    def test_invalid_google_analytics_id_is_ignored(self):
        context = seo_context(self.make_request("/"))

        self.assertEqual(context["google_analytics_measurement_id"], "")


class SeoEndpointContentTests(SimpleTestCase):
    @override_settings(SITE_URL="https://www.mindmetric.store")
    def test_sitemap_contains_public_pages_only(self):
        sitemap = PublicPageSitemap()
        locations = [sitemap.location(item) for item in sitemap.items()]
        absolute_locations = {
            item["location"] for item in sitemap.get_urls()
        }

        self.assertIn("/", locations)
        self.assertIn("/pricing/", locations)
        self.assertIn("/practice/", locations)
        self.assertIn("/practice/prepgia/", locations)
        self.assertIn(
            "/practice/prepgia/modules/reasoning/",
            locations,
        )
        self.assertNotIn("/dashboard/", locations)
        self.assertNotIn("/practice/prepgia/full-test/", locations)
        self.assertIn(
            "https://mindmetric.store/practice/prepgia/",
            absolute_locations,
        )

    def test_robots_points_to_canonical_sitemap(self):
        content = render_to_string(
            "robots.txt",
            {"site_url": "https://mindmetric.store"},
        )

        self.assertIn(
            "Sitemap: https://mindmetric.store/sitemap.xml",
            content,
        )
        self.assertIn("Disallow: /api/", content)


class SearchMetadataTests(SimpleTestCase):
    def test_thomas_gia_assessment_targets_full_name(self):
        metadata = assessment_seo_metadata("prepgia", "Thomas GIA")

        self.assertIn("Free Thomas GIA Practice Test", metadata["page_title"])
        self.assertIn(
            "Thomas International General Intelligence Assessment",
            metadata["meta_description"],
        )
        self.assertIn("free", metadata["meta_description"].lower())

    def test_thomas_gia_module_title_is_assessment_specific(self):
        metadata = module_seo_metadata(
            "prepgia",
            "reasoning",
            "Thomas GIA",
            "Reasoning",
            "Fallback",
        )

        self.assertIn("Thomas GIA Reasoning", metadata["page_title"])

    def test_ccat_uses_expanded_assessment_name(self):
        metadata = assessment_seo_metadata("ccat", "CCAT")

        self.assertIn("Free CCAT Practice Test", metadata["page_title"])
        self.assertIn(
            "Criteria Cognitive Aptitude Test",
            metadata["meta_description"],
        )
        self.assertIn("aptitude", metadata["page_title"].lower())
