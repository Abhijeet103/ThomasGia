from __future__ import annotations

import ipaddress
import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


logger = logging.getLogger(__name__)

COUNTRY_SESSION_KEY = "billing_country_code"

# Countries whose regional storefront price is shown in euros. Exact country
# rows in the admin still take precedence over this shared EU row.
EUROPEAN_COUNTRY_CODES = frozenset(
    {
        "AD", "AL", "AT", "AX", "BA", "BE", "BG", "BY", "CH", "CY",
        "CZ", "DE", "DK", "EE", "ES", "FI", "FO", "FR", "GG", "GI",
        "GR", "HR", "HU", "IE", "IM", "IS", "IT", "JE", "LI", "LT",
        "LU", "LV", "MC", "MD", "ME", "MK", "MT", "NL", "NO", "PL",
        "PT", "RO", "RS", "SE", "SI", "SK", "SM", "UA", "VA",
    }
)


def normalize_country_code(value: str | None) -> str | None:
    country_code = (value or "").strip().upper()
    if len(country_code) == 2 and country_code.isalpha():
        return country_code
    return None


def pricing_region_for_country(country_code: str | None) -> str:
    country_code = normalize_country_code(country_code)
    if country_code == "IN":
        return "IN"
    if country_code == "GB":
        return "GB"
    if country_code in EUROPEAN_COUNTRY_CODES:
        return "EU"
    return "US"


def price_override_codes(country_code: str | None) -> tuple[str, ...]:
    country_code = normalize_country_code(country_code)
    region = pricing_region_for_country(country_code)
    if country_code and country_code != region and region != "US":
        return country_code, region
    if region != "US":
        return (region,)
    return ()


def _country_from_proxy_header(request) -> str | None:
    if not settings.BILLING_TRUST_PROXY_COUNTRY_HEADERS:
        return None
    for header in settings.BILLING_COUNTRY_HEADERS:
        country_code = normalize_country_code(request.META.get(header))
        if country_code:
            return country_code
    return None


def _request_ip(request) -> str | None:
    raw_ip = request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
    if not raw_ip:
        return None
    try:
        address = ipaddress.ip_address(raw_ip.strip())
    except ValueError:
        return None
    if not address.is_global:
        return None
    return str(address)


def _lookup_ip_country(ip_address: str) -> str | None:
    url_template = settings.BILLING_IP_COUNTRY_LOOKUP_URL
    if not url_template:
        return None
    request = Request(
        url_template.format(ip=ip_address),
        headers={"Accept": "application/json,text/plain", "User-Agent": "MindMetric/1.0"},
    )
    try:
        with urlopen(request, timeout=settings.BILLING_IP_COUNTRY_LOOKUP_TIMEOUT) as response:
            raw_value = response.read().decode("utf-8").strip()
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        logger.info("Country lookup failed for billing request: %s", exc)
        return None

    try:
        payload = json.loads(raw_value)
    except json.JSONDecodeError:
        return normalize_country_code(raw_value)
    if isinstance(payload, dict):
        return normalize_country_code(
            payload.get("country_code") or payload.get("country")
        )
    return None


def _country_from_accept_language(request) -> str | None:
    for language in request.META.get("HTTP_ACCEPT_LANGUAGE", "").split(","):
        locale = language.split(";", 1)[0].strip().replace("_", "-")
        if "-" not in locale:
            continue
        country_code = normalize_country_code(locale.rsplit("-", 1)[-1])
        if country_code:
            return country_code
    return None


def get_request_country_code(request) -> str:
    saved_country = normalize_country_code(request.session.get(COUNTRY_SESSION_KEY))
    if saved_country:
        return saved_country

    country_code = _country_from_proxy_header(request)
    if not country_code:
        request_ip = _request_ip(request)
        country_code = _lookup_ip_country(request_ip) if request_ip else None
    if not country_code:
        country_code = _country_from_accept_language(request)
    country_code = country_code or "US"
    request.session[COUNTRY_SESSION_KEY] = country_code
    return country_code
