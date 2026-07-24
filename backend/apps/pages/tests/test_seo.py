import json

from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase, override_settings
from django.urls import resolve

from backend.apps.pages.seo import seo_context
from backend.apps.pages.sitemaps import PublicPageSitemap


@override_settings(
    SITE_URL="https://www.mindmetric.store",
    CONTACT_EMAIL="support@mindmetric.store",
    GOOGLE_SITE_VERIFICATION="verification-token",
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
