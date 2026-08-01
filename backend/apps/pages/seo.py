from __future__ import annotations

import json
import re
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.urls import reverse

from backend.apps.assessments.config import ASSESSMENT_CCAT, ASSESSMENT_PREPGIA


INDEXABLE_VIEWS = {
    "pages:home",
    "pages:pricing",
    "pages:practice",
    "pages:assessment-practice",
    "pages:assessment-section-detail",
}

GA4_MEASUREMENT_ID_PATTERN = re.compile(r"^G-[A-Z0-9]+$")

ASSESSMENT_SEO_METADATA = {
    ASSESSMENT_PREPGIA: {
        "page_title": "Free Thomas GIA Practice Test & Questions | MindMetric",
        "meta_description": (
            "Try a free Thomas GIA practice test with questions for all five sections "
            "of the Thomas International General Intelligence Assessment (GIA)."
        ),
        "schema_name": "Thomas GIA Practice Test",
    },
    ASSESSMENT_CCAT: {
        "page_title": "Free CCAT Practice Test & Aptitude Questions | MindMetric",
        "meta_description": (
            "Try free CCAT practice questions for the Criteria Cognitive Aptitude Test, "
            "including numerical, verbal, logic and spatial reasoning drills."
        ),
        "schema_name": "CCAT Practice Test",
    },
}

MODULE_SEO_METADATA = {
    ASSESSMENT_PREPGIA: {
        "reasoning": {
            "page_title": "Thomas GIA Reasoning Practice Test & Questions | MindMetric",
            "meta_description": (
                "Practice Thomas GIA Reasoning questions using comparisons, "
                "transitive logic and timed exercises for the Thomas International GIA."
            ),
        },
        "perceptual_speed": {
            "page_title": "Thomas GIA Perceptual Speed Practice Test | MindMetric",
            "meta_description": (
                "Practice Thomas GIA Perceptual Speed questions with timed letter-pair "
                "matching exercises for the General Intelligence Assessment."
            ),
        },
        "number_speed_accuracy": {
            "page_title": "Thomas GIA Number Speed & Accuracy Practice | MindMetric",
            "meta_description": (
                "Practice Thomas GIA Number Speed and Accuracy questions with timed "
                "numerical comparison exercises and immediate feedback."
            ),
        },
        "word_meaning": {
            "page_title": "Thomas GIA Word Meaning Practice Test | MindMetric",
            "meta_description": (
                "Practice Thomas GIA Word Meaning questions with vocabulary, "
                "word-group and odd-one-out exercises for the Thomas International GIA."
            ),
        },
        "spatial_visualization": {
            "page_title": "Thomas GIA Spatial Visualisation Practice Test | MindMetric",
            "meta_description": (
                "Practice Thomas GIA Spatial Visualisation questions covering rotated "
                "shapes, mirrored figures and fast visual comparisons."
            ),
        },
    },
    ASSESSMENT_CCAT: {
        "ccat_numerical": {
            "page_title": "CCAT Numerical Reasoning Practice Test | MindMetric",
            "meta_description": (
                "Practice Criteria CCAT numerical reasoning questions covering number "
                "series, ratios, percentages and quantitative problem solving."
            ),
        },
        "ccat_verbal": {
            "page_title": "CCAT Verbal Reasoning Practice Test | MindMetric",
            "meta_description": (
                "Practice Criteria CCAT verbal reasoning questions with analogies, "
                "vocabulary, sentence logic and word-group exercises."
            ),
        },
        "ccat_spatial": {
            "page_title": "CCAT Spatial & Abstract Reasoning Practice | MindMetric",
            "meta_description": (
                "Practice Criteria CCAT spatial and abstract reasoning questions "
                "covering visual patterns, transformations and non-verbal logic."
            ),
        },
    },
}


def assessment_seo_metadata(assessment_type: str, fallback_title: str) -> dict[str, str]:
    return ASSESSMENT_SEO_METADATA.get(
        assessment_type,
        {
            "page_title": f"{fallback_title} Practice Test | MindMetric",
            "meta_description": (
                f"Prepare for {fallback_title} with module practice, timed questions "
                "and full mock tests on MindMetric."
            ),
            "schema_name": f"{fallback_title} Practice Test",
        },
    )


def module_seo_metadata(
    assessment_type: str,
    module_key: str,
    assessment_title: str,
    module_title: str,
    fallback_description: str,
) -> dict[str, str]:
    return MODULE_SEO_METADATA.get(assessment_type, {}).get(
        module_key,
        {
            "page_title": (
                f"{assessment_title} {module_title} Practice Test | MindMetric"
            ),
            "meta_description": fallback_description,
        },
    )


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
                "url": f"{site_url}/static/favicons/android-chrome-512x512.png",
                "width": 512,
                "height": 512,
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
    elif view_name == "pages:assessment-practice":
        assessment_slug = request.resolver_match.kwargs.get("assessment_slug", "")
        metadata = assessment_seo_metadata(assessment_slug, assessment_slug.upper())
        graph.append(
            {
                "@type": "BreadcrumbList",
                "@id": f"{canonical_url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Practice Tests",
                        "item": f"{site_url}{reverse('pages:practice')}",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": metadata["schema_name"],
                        "item": canonical_url,
                    },
                ],
            }
        )
    elif view_name == "pages:assessment-section-detail":
        assessment_slug = request.resolver_match.kwargs.get("assessment_slug", "")
        module_slug = request.resolver_match.kwargs.get("slug", "")
        assessment_metadata = assessment_seo_metadata(
            assessment_slug,
            assessment_slug.upper(),
        )
        module_metadata = MODULE_SEO_METADATA.get(assessment_slug, {}).get(
            module_slug,
            {},
        )
        graph.append(
            {
                "@type": "BreadcrumbList",
                "@id": f"{canonical_url}#breadcrumb",
                "itemListElement": [
                    {
                        "@type": "ListItem",
                        "position": 1,
                        "name": "Practice Tests",
                        "item": f"{site_url}{reverse('pages:practice')}",
                    },
                    {
                        "@type": "ListItem",
                        "position": 2,
                        "name": assessment_metadata["schema_name"],
                        "item": (
                            f"{site_url}"
                            f"{reverse('pages:assessment-practice', args=[assessment_slug])}"
                        ),
                    },
                    {
                        "@type": "ListItem",
                        "position": 3,
                        "name": module_metadata.get(
                            "page_title",
                            module_slug.replace("_", " ").title(),
                        ).split(" | ", 1)[0],
                        "item": canonical_url,
                    },
                ],
            }
        )

    return {
        "seo_canonical_url": canonical_url,
        "seo_robots_content": robots_content,
        "seo_social_image_url": (
            f"{site_url}/static/favicons/android-chrome-512x512.png"
        ),
        "seo_social_image_alt": "MindMetric psychometric test practice platform",
        "seo_schema_json": json.dumps(
            {
                "@context": "https://schema.org",
                "@graph": graph,
            },
            separators=(",", ":"),
        ),
        "google_site_verification": settings.GOOGLE_SITE_VERIFICATION,
        "google_analytics_measurement_id": (
            settings.GOOGLE_ANALYTICS_MEASUREMENT_ID
            if settings.IS_PRODUCTION
            and GA4_MEASUREMENT_ID_PATTERN.fullmatch(settings.GOOGLE_ANALYTICS_MEASUREMENT_ID)
            else ""
        ),
        "google_analytics_tenant_slug": getattr(getattr(request, "tenant", None), "slug", ""),
        "thomas_gia_blog_url": settings.THOMAS_GIA_BLOG_URL,
    }
