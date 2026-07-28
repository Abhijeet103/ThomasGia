(() => {
  const script = document.currentScript;
  const measurementId = script?.dataset.measurementId || "";
  const tenantSlug = script?.dataset.tenantSlug || "";
  const consentKey = "mindmetric_analytics_consent";

  if (!/^G-[A-Z0-9]+$/.test(measurementId)) {
    return;
  }

  const readConsent = () => {
    try {
      return window.localStorage.getItem(consentKey);
    } catch {
      return null;
    }
  };

  const saveConsent = (value) => {
    try {
      window.localStorage.setItem(consentKey, value);
    } catch {
      // The current page still respects the choice when storage is unavailable.
    }
  };

  const loadAnalytics = () => {
    if (window.dataLayer) {
      return;
    }

    window.dataLayer = [];
    window.gtag = function gtag() {
      window.dataLayer.push(arguments);
    };
    window.gtag("js", new Date());
    window.gtag("config", measurementId, {
      tenant_slug: tenantSlug || "mindmetric",
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
    });

    const googleTag = document.createElement("script");
    googleTag.async = true;
    googleTag.src = `https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(measurementId)}`;
    document.head.appendChild(googleTag);
  };

  const initializeConsent = () => {
    const banner = document.querySelector("[data-analytics-consent]");
    const consent = readConsent();

    if (consent === "granted") {
      loadAnalytics();
      return;
    }

    if (consent === "denied" || !banner) {
      return;
    }

    banner.hidden = false;
    banner.querySelector("[data-analytics-accept]")?.addEventListener("click", () => {
      saveConsent("granted");
      banner.hidden = true;
      loadAnalytics();
    });
    banner.querySelector("[data-analytics-reject]")?.addEventListener("click", () => {
      saveConsent("denied");
      banner.hidden = true;
    });
  };

  document.addEventListener("DOMContentLoaded", initializeConsent, { once: true });
})();
