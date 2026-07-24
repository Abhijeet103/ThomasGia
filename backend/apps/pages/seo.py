from __future__ import annotations

import json
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.urls import reverse


INDEXABLE_VIEWS = {
    "pages:home",
    "pages:pricing",
    "pages:practice",
    "pages:assessment-practice",
    "pages:assessment-section-detail",
}


def canonical_site_url() -> str:
    configured_url = settings.SITE_URL.rstrip("/")
    parsed = urlparse(configured_url)
    hostname = parsed.hostname or ""
    if hostname.startswith("www."):
        hostname = hostname[4:]
        port = f":{parsed.port}" if parsed.port else ""
        parsed = parsed._replace(netloc=f"{hostname}{port}")
    return urlunparse(parsed).rstrip("/")


def _canonical_path(request) -> str:
    match = request.resolver_match
    if match and match.view_name == "pages:section-detail":
        return reverse(
            "pages:assessment-section-detail",
            args=["prepgia", match.kwargs["slug"]],
        )
    if match and match.view_name == "pages:full-test":
        return reverse("pages:assessment-full-test", args=["prepgia"])
    return request.path


def seo_context(request):
    site_url = canonical_site_url()
    canonical_url = f"{site_url}{_canonical_path(request)}"
    view_name = request.resolver_match.view_name if request.resolver_match else ""
    robots_content = "index,follow" if view_name in INDEXABLE_VIEWS else "noindex,nofollow"

    graph = [
        {
            "@type": "Organization",
            "@id": f"{site_url}/#organization",
            "name": "MindMetric",
            "url": f"{site_url}/",
            "logo": {
                "@type": "ImageObject",
                "url": f"{site_url}/static/apple-touch-icon.png",
            },
            "email": settings.CONTACT_EMAIL,
        },
        {
            "@type": "WebSite",
            "@id": f"{site_url}/#website",
            "name": "MindMetric",
            "url": f"{site_url}/",
            "publisher": {"@id": f"{site_url}/#organization"},
        },
    ]
    if view_name == "pages:home":
        graph.append(
            {
                "@type": "WebApplication",
                "name": "MindMetric",
                "url": f"{site_url}/",
                "applicationCategory": "EducationalApplication",
                "operatingSystem": "Web",
                "description": "Cognitive and psychometric test practice with module drills and full mock tests.",
                "offers": {
                    "@type": "Offer",
                    "price": "0",
                    "priceCurrency": "USD",
                },
                "publisher": {"@id": f"{site_url}/#organization"},
            }
        )

    return {
        "seo_canonical_url": canonical_url,
        "seo_robots_content": robots_content,
        "seo_schema_json": json.dumps(
            {
                "@context": "https://schema.org",
                "@graph": graph,
            },
            separators=(",", ":"),
        ),
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
    }
