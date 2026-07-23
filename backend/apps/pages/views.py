from __future__ import annotations

import logging
import uuid
from dataclasses import asdict

from allauth.account.forms import LoginForm
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.generic import TemplateView
from django.db.models import Prefetch
from django.views import View
from django.views.generic.edit import FormView

from backend.apps.billing.services import (
    build_plan_cards,
    paypal_is_configured,
    stripe_is_configured,
    sync_user_subscription_access,
)
from backend.apps.tenants.utils import get_default_tenant
from backend.apps.assessments.config import (
    ASSESSMENT_CCAT,
    ASSESSMENT_PREPGIA,
    get_assessment_cards,
    get_assessment_config,
    get_assessment_module_keys,
    get_module_meta,
    get_time_limit_seconds,
)
from backend.apps.assessments.models import AttemptMode, AttemptSection, AttemptStatus, SectionProgress, SectionType
from backend.apps.assessments.services import (
    FullTestSessionError,
    can_start_attempt,
    expire_stale_attempts,
    get_or_create_full_test_attempt,
    get_or_create_section_attempt,
    get_section_test_previews,
    serialize_full_test_attempt_for_frontend,
)
from .emails import send_sale_inquiry_notification
from .forms import SaleInquiryForm
from prepgia.generators import generate_question
from prepgia.preview_data import get_questions

SECTION_PRACTICE_GENERATION_COUNT = 40
SECTION_PRACTICE_PAID_COUNT = 100
SECTION_PRACTICE_GOAL = 50
logger = logging.getLogger(__name__)


ESTIMATE_BASELINES = {
    ASSESSMENT_PREPGIA: {
        "full_test": 56,
        "reasoning": 57,
        "perceptual_speed": 54,
        "number_speed_accuracy": 55,
        "word_meaning": 58,
        "spatial_visualization": 53,
    },
    ASSESSMENT_CCAT: {
        "full_test": 58,
        "ccat_numerical": 57,
        "ccat_verbal": 59,
        "ccat_spatial": 56,
    },
}


def _estimate_percentile(score: float | int | None, assessment_type: str, section_type: str | None = None) -> int:
    if score is None:
        return 1
    baseline_map = ESTIMATE_BASELINES.get(assessment_type, {})
    baseline_key = str(section_type) if section_type else "full_test"
    baseline = baseline_map.get(baseline_key, baseline_map.get("full_test", 55))
    percentile = round(50 + (float(score) - baseline) * 1.6)
    return max(1, min(99, percentile))


def _estimate_iq_band(percentile: int) -> tuple[str, str]:
    if percentile >= 98:
        return "130+", "Very superior range"
    if percentile >= 91:
        return "120-129", "Superior range"
    if percentile >= 75:
        return "110-119", "High average range"
    if percentile >= 25:
        return "90-109", "Average range"
    if percentile >= 10:
        return "80-89", "Low average range"
    return "Below 80", "Developing range"


def _build_estimate(score: float | int | None, assessment_type: str, section_type: str | None = None) -> dict[str, object]:
    percentile = _estimate_percentile(score, assessment_type, section_type)
    iq_range, band = _estimate_iq_band(percentile)
    return {
        "percentile": percentile,
        "percentile_label": f"{percentile}th percentile",
        "iq_range": iq_range,
        "band": band,
    }


def _contact_form_initial(request, source_page: str) -> dict[str, str]:
    initial = {"source_page": source_page}
    if request.user.is_authenticated:
        initial.update(
            {
                "email": request.user.email or "",
            }
        )
    return initial


def _visible_frontend_plans(user, active_subscription):
    return [plan for plan in build_plan_cards(user, active_subscription) if plan["code"] != "yearly"]


def _contact_sales_open_url(request) -> str:
    return f"{request.path}?contact_sales=open"


def _contact_sales_close_url(request) -> str:
    return request.path


def _format_remaining_time(expires_at):
    if not expires_at:
        return "No active expiry"
    now = timezone.now()
    if expires_at <= now:
        return "Expired"
    delta = expires_at - now
    days = delta.days
    if days >= 365:
        years = days // 365
        months = max(0, (days % 365) // 30)
        if months:
            return f"About {years} year{'s' if years != 1 else ''} {months} month{'s' if months != 1 else ''} remaining"
        return f"About {years} year{'s' if years != 1 else ''} remaining"
    if days >= 30:
        months = days // 30
        extra_days = days % 30
        if extra_days:
            return f"About {months} month{'s' if months != 1 else ''} {extra_days} day{'s' if extra_days != 1 else ''} remaining"
        return f"About {months} month{'s' if months != 1 else ''} remaining"
    if days >= 7:
        weeks = days // 7
        extra_days = days % 7
        if extra_days:
            return f"About {weeks} week{'s' if weeks != 1 else ''} {extra_days} day{'s' if extra_days != 1 else ''} remaining"
        return f"About {weeks} week{'s' if weeks != 1 else ''} remaining"
    if days >= 1:
        return f"About {days} day{'s' if days != 1 else ''} remaining"
    hours = max(1, delta.seconds // 3600)
    return f"About {hours} hour{'s' if hours != 1 else ''} remaining"


def _plan_title(active_subscription) -> str:
    if not active_subscription:
        return "Free plan"
    return f"{active_subscription.plan_code.replace('_', ' ').title()} plan"


class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prepgia_config = get_assessment_config(ASSESSMENT_PREPGIA)
        all_questions = get_questions()
        context.update(
            {
                "page_title": "MindMetric | Cognitive And Psychometric Test Practice Platform",
                "meta_description": "Practice CCAT and Thomas GIA-style cognitive tests with module drills, full mocks, Google login, and subscription access.",
                "question_count": len(all_questions),
                "sections": _section_cards(ASSESSMENT_PREPGIA),
                "home_assessments": get_assessment_cards(),
                "home_eyebrow": prepgia_config["eyebrow"],
            }
        )
        return context


class PricingPageView(TemplateView):
    template_name = "pages/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_subscription = None
        if self.request.user.is_authenticated:
            sync_user_subscription_access(self.request.user)
            active_subscription = self.request.user.subscriptions.filter(status="active").order_by("-updated_at").first()
        context.update(
            {
                "page_title": "Pricing | MindMetric",
                "meta_description": "View free and paid plans for MindMetric practice tests.",
                "active_subscription": active_subscription,
                "plans": _visible_frontend_plans(self.request.user, active_subscription),
                "paypal_enabled": paypal_is_configured(),
                "stripe_enabled": stripe_is_configured(),
                "contact_form": SaleInquiryForm(initial={**_contact_form_initial(self.request, "pricing"), "next": self.request.path}),
                "contact_sales_open_url": _contact_sales_open_url(self.request),
                "contact_sales_close_url": _contact_sales_close_url(self.request),
            }
        )
        return context


class SubscriptionPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/subscription.html"
    login_url = "/login/"

    def dispatch(self, request, *args, **kwargs):
        sync_user_subscription_access(request.user)
        if not request.user.has_active_subscription:
            return redirect("pages:pricing")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_subscription = self.request.user.subscriptions.filter(status="active").order_by("-updated_at").first()
        visible_plans = _visible_frontend_plans(self.request.user, active_subscription)
        extension_cards = []
        for plan in visible_plans:
            extension_cards.append(
                {
                    **plan,
                    "show_action": True,
                    "button_label": "Add 7 days" if plan["code"] == "weekly" else "Add 1 month",
                    "is_disabled": False,
                    "extension_code": "+7d" if plan["code"] == "weekly" else "+1m",
                    "extension_title": "Add 7 days" if plan["code"] == "weekly" else "Add 1 month",
                    "extension_copy": "Add 7 days of access" if plan["code"] == "weekly" else "Add 1 month of access",
                }
            )
        context.update(
            {
                "page_title": "Subscription | MindMetric",
                "meta_description": "View your MindMetric subscription status and manage cancellation.",
                "active_subscription": active_subscription,
                "subscription_expires_at": self.request.user.subscription_expires_at,
                "plans": visible_plans,
                "extension_cards": extension_cards,
                "paypal_enabled": paypal_is_configured(),
                "stripe_enabled": stripe_is_configured(),
                "checkout_state": self.request.GET.get("checkout", ""),
                "contact_form": SaleInquiryForm(initial={**_contact_form_initial(self.request, "subscription"), "next": self.request.path}),
                "contact_sales_open_url": _contact_sales_open_url(self.request),
                "contact_sales_close_url": _contact_sales_close_url(self.request),
                "subscription_plan_title": _plan_title(active_subscription),
                "subscription_is_active": bool(active_subscription and self.request.user.subscription_expires_at),
                "subscription_access_summary": "Full access, all tracks" if active_subscription else "Free access with limited section practice",
                "subscription_remaining_copy": _format_remaining_time(self.request.user.subscription_expires_at),
            }
        )
        return context


class ContactInquiryCreateView(FormView):
    form_class = SaleInquiryForm
    http_method_names = ["post"]

    def form_valid(self, form):
        form.instance.tenant = (
            getattr(self.request, "tenant", None)
            or getattr(self.request.user, "tenant", None)
            or get_default_tenant()
        )
        inquiry = form.save()
        logger.info("Saved sales inquiry id=%s source=%s email=%s", inquiry.id, inquiry.source_page, inquiry.email)
        try:
            send_sale_inquiry_notification(inquiry)
        except Exception as exc:
            logger.exception("Failed to send sale inquiry notification for inquiry id=%s", inquiry.id)
            messages.warning(
                self.request,
                "Your inquiry was saved, but the notification email could not be sent right now."
            )
            return redirect(self.get_success_url(form))

        messages.success(self.request, "Thanks. We will contact you soon.")
        return redirect(self.get_success_url(form))

    def form_invalid(self, form):
        messages.error(self.request, "Please complete the contact sales form and try again.")
        return redirect(self.get_success_url(form, fallback="pages:pricing", with_modal=True))

    def get_success_url(self, form, fallback: str = "pages:pricing", with_modal: bool = False):
        next_url = form.cleaned_data.get("next") or self.request.POST.get("next") or self.request.META.get("HTTP_REFERER")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()):
            if with_modal:
                separator = "&" if "?" in next_url else "?"
                return f"{next_url}{separator}contact_sales=open"
            return next_url
        url = reverse(fallback)
        if with_modal:
            return f"{url}?contact_sales=open"
        return url


class PracticePageView(TemplateView):
    template_name = "pages/practice_selector.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Practice | MindMetric",
                "meta_description": "Choose between Thomas GIA and CCAT practice tracks.",
                "assessments": get_assessment_cards(),
            }
        )
        return context


class AssessmentPracticePageView(TemplateView):
    template_name = "pages/practice.html"

    def get_context_data(self, **kwargs):
        from backend.apps.assessments.services import FREE_FULL_TEST_LIMIT, FREE_SECTION_TEST_LIMIT
        from backend.apps.accounts.models import UserRole
        from backend.apps.assessments.models import Attempt, AttemptMode
        context = super().get_context_data(**kwargs)
        assessment_type = self.kwargs["assessment_slug"]
        assessment_config = get_assessment_config(assessment_type)
        sections = _practice_section_cards(self.request, assessment_type)
        user = self.request.user
        if user.is_authenticated and getattr(user, "role", UserRole.FREE) == UserRole.PAID:
            full_test_attempts_left = None
            module_test_attempts_left = None
        elif user.is_authenticated:
            full_used = Attempt.objects.filter(user=user, mode=AttemptMode.FULL_TEST, assessment_type=assessment_type).count()
            module_used = Attempt.objects.filter(user=user, mode=AttemptMode.SECTION, assessment_type=assessment_type).count()
            full_test_attempts_left = max(0, FREE_FULL_TEST_LIMIT - full_used)
            module_test_attempts_left = max(0, FREE_SECTION_TEST_LIMIT - module_used)
        else:
            full_test_attempts_left = FREE_FULL_TEST_LIMIT
            module_test_attempts_left = FREE_SECTION_TEST_LIMIT
        context.update(
            {
                "page_title": f"{assessment_config['title']} Practice | MindMetric",
                "meta_description": f"Choose full test or module-wise practice for {assessment_config['title']}.",
                "assessment": assessment_config,
                "assessment_slug": assessment_type,
                "sections": sections,
                "sections_started": sum(1 for section in sections if section["status_class"] != "status-not-started"),
                "sections_total": len(sections),
                "full_test_attempts_left": full_test_attempts_left,
                "module_test_attempts_left": module_test_attempts_left,
            }
        )
        return context


class SectionsPageView(TemplateView):
    template_name = "pages/sections.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sections = []
        for key in get_assessment_module_keys(ASSESSMENT_PREPGIA):
            meta = get_module_meta(key)
            sections.append(
                {
                    "key": key,
                    "title": meta["title"],
                    "description": meta["description"],
                    "time_limit_seconds": get_time_limit_seconds(key),
                    "sample_count": len(get_questions(key)),
                }
            )
        context.update(
            {
                "page_title": "Sections | MindMetric",
                "meta_description": "Browse all five Thomas GIA-style sections available in MindMetric.",
                "sections": sections,
            }
        )
        return context


class FullTestPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/full_test.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment_type = self.kwargs.get("assessment_slug", ASSESSMENT_PREPGIA)
        assessment_config = get_assessment_config(assessment_type)
        section_meta = {module["key"]: {"title": module["title"], "description": module["description"]} for module in assessment_config["modules"]}
        instructions = {module["key"]: module["instruction"] for module in assessment_config["modules"]}
        full_test_data = []
        full_test_attempt_id = None
        access_error = None
        try:
            attempt = get_or_create_full_test_attempt(self.request.user, assessment_type=assessment_type)
            full_test_attempt_id = attempt.id
            full_test_data = serialize_full_test_attempt_for_frontend(
                attempt,
                section_meta,
                instructions,
                assessment_config["full_test_practice_count"],
            )
        except PermissionError as exc:
            access_error = str(exc)
        except FullTestSessionError:
            logger.exception("Full test setup failed because the active Redis-backed session was unavailable.")
            access_error = "Full test is temporarily unavailable. Please try again in a moment."
        context.update(
            {
                "page_title": f"{assessment_config['title']} Full Test | MindMetric",
                "meta_description": f"Run through all {assessment_config['title']} modules in one guided flow with practice and timed test phases.",
                "assessment": assessment_config,
                "assessment_slug": assessment_type,
                "full_test_data": full_test_data,
                "full_test_attempt_id": full_test_attempt_id,
                "full_test_question_url": f"/api/tests/full-tests/{full_test_attempt_id}/question/" if full_test_attempt_id else "",
                "full_test_submit_url": f"/api/tests/full-tests/{full_test_attempt_id}/submit/" if full_test_attempt_id else "",
                "full_test_access_error": access_error,
            }
        )
        return context


class SectionDetailPageView(TemplateView):
    template_name = "pages/section_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        assessment_type = self.kwargs.get("assessment_slug", ASSESSMENT_PREPGIA)
        assessment_config = get_assessment_config(assessment_type)
        slug = self.kwargs["slug"]
        try:
            section_type = SectionType(slug)
        except ValueError as exc:
            raise Http404("Section not found.") from exc
        if section_type not in get_assessment_module_keys(assessment_type):
            raise Http404("Section not found.")

        mode = self.request.GET.get("mode", "practice")
        if mode not in {"practice", "test"}:
            mode = "practice"

        meta = get_module_meta(section_type)
        section_attempt_id = None
        section_submit_url = ""
        section_access_error = ""
        section_access_requires_upgrade = False
        practice_question_total = max(1, get_time_limit_seconds(section_type) // 2)
        practice_questions_solved = 0
        if self.request.user.is_authenticated:
            progress = SectionProgress.objects.filter(
                user=self.request.user,
                assessment_type=assessment_type,
                section_type=section_type,
            ).first()
            if progress is not None:
                practice_questions_solved = progress.practice_questions_solved
        practice_progress_percent = min(round((practice_questions_solved / practice_question_total) * 100), 100) if practice_question_total else 0
        if mode == "test" and self.request.user.is_authenticated:
            try:
                attempt = get_or_create_section_attempt(self.request.user, section_type, assessment_type=assessment_type)
                section_attempt_id = attempt.id
                previews = get_section_test_previews(attempt)
                section_submit_url = f"/api/tests/section-tests/{section_attempt_id}/submit/" if section_attempt_id else ""
            except PermissionError as exc:
                section_access_error = str(exc)
                section_access_requires_upgrade = True
                previews = []
            except FullTestSessionError:
                logger.exception("Section test setup failed because the active Redis-backed session was unavailable.")
                section_access_error = "Section test is temporarily unavailable. Please try again in a moment."
                previews = []
        else:
            previews = _build_section_questions(section_type, mode, user=self.request.user)
        context.update(
            {
                "page_title": f"{meta['title']} {mode.title()} | MindMetric",
                "meta_description": meta["description"],
                "assessment": assessment_config,
                "assessment_slug": assessment_type,
                "section": {
                    "key": section_type,
                    "title": meta["title"],
                    "description": meta["description"],
                    "instruction": meta["instruction"],
                    "time_limit_seconds": get_time_limit_seconds(section_type),
                    "question_count": len(previews),
                    "practice_question_total": practice_question_total,
                    "practice_questions_solved": practice_questions_solved,
                    "practice_progress_percent": practice_progress_percent,
                    "previews": previews,
                    "mode": mode,
                    "attempt_id": section_attempt_id,
                    "submit_url": section_submit_url,
                    "access_error": section_access_error,
                    "access_requires_upgrade": section_access_requires_upgrade,
                },
            }
        )
        return context


class LoginPageView(View):
    template_name = "pages/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("pages:dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = LoginForm(request=request)
        return render(request, self.template_name, self._context(request, form))

    def post(self, request, *args, **kwargs):
        form = LoginForm(request.POST, request=request)
        if form.is_valid():
            response = form.login(request, redirect_url=self._redirect_url(request))
            if response:
                return response
            return redirect(self._redirect_url(request))
        return render(request, self.template_name, self._context(request, form))

    def _redirect_url(self, request):
        return request.GET.get("next") or request.POST.get("next") or settings.LOGIN_REDIRECT_URL

    def _context(self, request, form):
        return {
            "page_title": "Login | MindMetric",
            "meta_description": "Sign in to MindMetric with email and password or continue with Google.",
            "google_login_path": "/accounts/google/login/",
            "form": form,
            "next_value": request.GET.get("next", ""),
        }


class DashboardPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempts = (
            self.request.user.attempts
            .prefetch_related(
                Prefetch(
                    "sections",
                    queryset=AttemptSection.objects.order_by("order_index"),
                )
            )
            .order_by("-started_at")
        )
        recent_attempts = attempts[:5]
        active_attempts = [attempt for attempt in attempts if attempt.status in {AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS}]
        full_test_attempts = [attempt for attempt in attempts if attempt.mode == AttemptMode.FULL_TEST and attempt.status == "completed"][:10]
        section_attempts = [attempt for attempt in attempts if attempt.mode == AttemptMode.SECTION and attempt.status == "completed"][:20]
        active_attempt_rows = []
        for attempt in active_attempts:
            first_section = next(iter(attempt.sections.all()), None)
            section_title = get_module_meta(first_section.section_type)["title"] if first_section else "-"
            continue_url = reverse("pages:assessment-full-test", args=[attempt.assessment_type]) if attempt.mode == AttemptMode.FULL_TEST else ""
            if attempt.mode == AttemptMode.SECTION and first_section:
                continue_url = f"{reverse('pages:assessment-section-detail', args=[attempt.assessment_type, first_section.section_type])}?mode=test"
            active_attempt_rows.append(
                {
                    "attempt_id": attempt.id,
                    "assessment_key": attempt.assessment_type,
                    "assessment_title": get_assessment_config(attempt.assessment_type)["title"],
                    "mode_label": attempt.get_mode_display(),
                    "section_title": section_title,
                    "status_label": attempt.get_status_display(),
                    "started_at": attempt.started_at,
                    "continue_url": continue_url,
                    "end_url": reverse("attempt-end", args=[attempt.id]),
                }
            )

        recent_attempt_rows = []
        for attempt in recent_attempts:
            first_section = next(iter(attempt.sections.all()), None)
            estimate = _build_estimate(
                attempt.overall_adjusted_score,
                attempt.assessment_type,
                first_section.section_type if attempt.mode == AttemptMode.SECTION and first_section else None,
            )
            recent_attempt_rows.append(
                {
                    "attempt_id": attempt.id,
                    "assessment_key": attempt.assessment_type,
                    "assessment_title": get_assessment_config(attempt.assessment_type)["title"],
                    "mode_label": attempt.get_mode_display(),
                    "section_title": get_module_meta(first_section.section_type)["title"] if first_section else "-",
                    "status_label": attempt.get_status_display(),
                    "score": attempt.overall_adjusted_score,
                    "estimate_percentile_label": estimate["percentile_label"],
                    "estimate_band": estimate["band"],
                    "started_at": attempt.started_at,
                    "completed_at": attempt.completed_at,
                }
            )

        section_score_rows = []
        for attempt in section_attempts:
            section = next(iter(attempt.sections.all()), None)
            if section is None:
                continue
            estimate = _build_estimate(section.adjusted_score, attempt.assessment_type, section.section_type)
            section_score_rows.append(
                {
                    "attempt_id": attempt.id,
                    "assessment_key": attempt.assessment_type,
                    "assessment_title": get_assessment_config(attempt.assessment_type)["title"],
                    "section_title": get_module_meta(section.section_type)["title"],
                    "score": section.adjusted_score,
                    "estimate_percentile_label": estimate["percentile_label"],
                    "estimate_iq_range": estimate["iq_range"],
                    "question_count": section.question_count,
                    "time_limit_seconds": section.time_limit_seconds,
                    "completed_at": attempt.completed_at,
                }
            )

        full_test_rows = []
        for attempt in full_test_attempts:
            section_scores = {section.section_type: section.adjusted_score for section in attempt.sections.all()}
            module_keys = get_assessment_module_keys(attempt.assessment_type)
            estimate = _build_estimate(attempt.overall_adjusted_score, attempt.assessment_type)
            full_test_rows.append(
                {
                    "attempt_id": attempt.id,
                    "assessment_key": attempt.assessment_type,
                    "assessment_title": get_assessment_config(attempt.assessment_type)["title"],
                    "completed_at": attempt.completed_at,
                    "overall_score": attempt.overall_adjusted_score,
                    "estimate_percentile_label": estimate["percentile_label"],
                    "estimate_iq_range": estimate["iq_range"],
                    "ordered_section_scores": [section_scores.get(key, "-") for key in module_keys],
                    "module_score_summary": ", ".join(
                        f"{get_module_meta(key)['title']}: {section_scores.get(key, '-')}" for key in module_keys
                    ),
                }
            )

        # Build chart data keyed by "full_test" and each section type
        chart_data = {}
        assessment_cards = []
        assessment_estimates = {}
        for assessment_key in (ASSESSMENT_PREPGIA, ASSESSMENT_CCAT):
            config = get_assessment_config(assessment_key)
            assessment_cards.append(
                {
                    "key": assessment_key,
                    "title": config["title"],
                    "description": config["description"],
                    "module_count": len(config["modules"]),
                }
            )
            chart_data[assessment_key] = {"full_test": []}
            assessment_estimates[assessment_key] = {
                "percentile_label": "No estimate yet",
                "iq_range": "-",
                "band": "Complete a test to unlock an estimated range.",
                "based_on": "No completed attempts yet",
            }
            for module in config["modules"]:
                chart_data[assessment_key][str(module["key"])] = []

        for i, attempt in enumerate(reversed(full_test_attempts), start=1):
            score = attempt.overall_adjusted_score
            label = attempt.completed_at.strftime("%-d %b") if attempt.completed_at else f"#{i}"
            estimate = _build_estimate(score, attempt.assessment_type)
            chart_data[attempt.assessment_type]["full_test"].append(
                {
                    "label": label,
                    "score": score if score is not None else 0,
                    "percentile": estimate["percentile"],
                }
            )

        section_chart_attempts = (
            self.request.user.attempts.filter(mode=AttemptMode.SECTION, status="completed")
            .prefetch_related(Prefetch("sections", queryset=AttemptSection.objects.order_by("order_index")))
            .order_by("completed_at")
        )
        section_counters = {
            assessment_key: {str(module["key"]): 0 for module in get_assessment_config(assessment_key)["modules"]}
            for assessment_key in (ASSESSMENT_PREPGIA, ASSESSMENT_CCAT)
        }
        for attempt in section_chart_attempts:
            section = next(iter(attempt.sections.all()), None)
            if section is None:
                continue
            if section.section_type not in get_assessment_module_keys(attempt.assessment_type):
                continue
            key = str(section.section_type)
            section_counters[attempt.assessment_type][key] += 1
            label = attempt.completed_at.strftime("%-d %b") if attempt.completed_at else f"#{section_counters[attempt.assessment_type][key]}"
            score = section.adjusted_score
            estimate = _build_estimate(score, attempt.assessment_type, section.section_type)
            chart_data[attempt.assessment_type][key].append(
                {
                    "label": label,
                    "score": score if score is not None else 0,
                    "percentile": estimate["percentile"],
                }
            )

        for assessment_key in (ASSESSMENT_PREPGIA, ASSESSMENT_CCAT):
            latest_attempt = next(
                (
                    attempt for attempt in attempts
                    if attempt.assessment_type == assessment_key and attempt.status == AttemptStatus.COMPLETED
                ),
                None,
            )
            if latest_attempt is None:
                continue
            first_section = next(iter(latest_attempt.sections.all()), None)
            estimate = _build_estimate(
                latest_attempt.overall_adjusted_score,
                latest_attempt.assessment_type,
                first_section.section_type if latest_attempt.mode == AttemptMode.SECTION and first_section else None,
            )
            based_on = "Based on latest full test" if latest_attempt.mode == AttemptMode.FULL_TEST else "Based on latest module test"
            assessment_estimates[assessment_key] = {
                "percentile_label": estimate["percentile_label"],
                "iq_range": estimate["iq_range"],
                "band": estimate["band"],
                "based_on": based_on,
            }

        section_tabs = {
            assessment_key: [
                {"key": module["key"], "title": module["title"]}
                for module in get_assessment_config(assessment_key)["modules"]
            ]
            for assessment_key in (ASSESSMENT_PREPGIA, ASSESSMENT_CCAT)
        }

        context.update(
            {
                "page_title": "Dashboard | MindMetric",
                "meta_description": "Track your MindMetric access, attempts, and progress.",
                "active_attempt_rows": active_attempt_rows,
                "attempts": recent_attempt_rows,
                "full_test_rows": full_test_rows,
                "section_score_rows": section_score_rows,
                "expired_attempt_count": 0,
                "assessment_cards": assessment_cards,
                "assessment_estimates": assessment_estimates,
                "chart_data": chart_data,
                "section_tabs": section_tabs,
                "default_assessment_key": ASSESSMENT_PREPGIA,
            }
        )
        return context


def _section_cards(assessment_type: str):
    return [
        {"key": key, "title": get_module_meta(key)["title"], "description": get_module_meta(key)["description"], "sample_count": len(get_questions(key))}
        for key in get_assessment_module_keys(assessment_type)
    ]


def _practice_section_cards(request, assessment_type: str):
    progress_by_section = {}
    active_attempts = {}
    if request.user.is_authenticated:
        progress_by_section = {
            item.section_type: item
            for item in SectionProgress.objects.filter(user=request.user, assessment_type=assessment_type)
        }
        for attempt in (
            request.user.attempts.filter(
                assessment_type=assessment_type,
                mode=AttemptMode.SECTION,
                status__in=[AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS],
            )
            .prefetch_related(
                Prefetch("sections", queryset=AttemptSection.objects.order_by("order_index"))
            )
            .order_by("-started_at")
        ):
            first_section = next(iter(attempt.sections.all()), None)
            if first_section and first_section.section_type not in active_attempts:
                active_attempts[first_section.section_type] = attempt

    cards = []
    for index, key in enumerate(get_assessment_module_keys(assessment_type)):
        meta = get_module_meta(key)
        progress = progress_by_section.get(key)
        practice_solved = progress.practice_questions_solved if progress else 0
        tests_taken = progress.tests_taken if progress else 0
        active_attempt = active_attempts.get(key)
        practice_goal = SECTION_PRACTICE_GOAL
        test_goal = 10
        practice_ratio = min(practice_solved / practice_goal, 1) if practice_goal else 0
        test_ratio = min(tests_taken / test_goal, 1) if test_goal else 0
        progress_percent = round((practice_ratio * 0.5 + test_ratio * 0.5) * 100)

        if progress_percent >= 100:
            status_label = "Completed"
            status_class = "status-completed"
        elif active_attempt or practice_solved > 0 or tests_taken > 0:
            status_label = "In progress"
            status_class = "status-in-progress"
        else:
            status_label = "Not started"
            status_class = "status-not-started"

        is_started = status_class != "status-not-started"
        action_label = "Resume" if is_started else "Start"

        cards.append(
            {
                "key": key,
                "title": meta["title"],
                "description": meta["description"],
                "question_count": max(1, get_time_limit_seconds(key) // 2),
                "duration_minutes": max(1, get_time_limit_seconds(key) // 60),
                "practice_solved": practice_solved,
                "tests_taken": tests_taken,
                "progress_percent": progress_percent,
                "status_label": status_label,
                "status_class": status_class,
                "action_label": action_label,
                "action_class": "practice-button-secondary" if status_class == "status-in-progress" else "practice-button-primary",
                "action_url": f"{reverse('pages:assessment-section-detail', args=[assessment_type, key])}?mode=practice",
                "theme_class": f"section-theme-{index % 3}",
            }
        )
    return cards


def _build_section_questions(section_type: str, mode: str, user=None) -> list[dict]:
    difficulty = "easy" if mode == "practice" else "medium"
    if mode == "practice":
        question_count = max(1, get_time_limit_seconds(section_type) // 2)
    else:
        question_count = get_time_limit_seconds(section_type)
    session_id = uuid.uuid4().hex
    questions = []
    for index in range(question_count):
        seed = f"section:{section_type}:{mode}:{difficulty}:{session_id}:{index}"
        generated = generate_question(section_type, difficulty, seed)
        questions.append(_build_generated_preview(asdict(generated)))
    return questions


def _question_summary(payload_json: str) -> str:
    import json

    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        return "Question preview unavailable."

    prompt = payload.get("prompt", {})
    if "question" in prompt:
        return prompt["question"]
    if "instruction" in prompt and "words" in prompt:
        return f"{prompt['instruction']} {' / '.join(prompt['words'])}"
    if "instruction" in prompt and "numbers" in prompt:
        return f"{prompt['instruction']} {' / '.join(str(number) for number in prompt['numbers'])}"
    return prompt.get("instruction", "Question preview unavailable.")


def _build_preview(item: dict, section_type: str) -> dict:
    import json

    payload_json = item["question_payload_json"]
    correct_answer_json = item["correct_answer_json"]
    preview = {
        "seed": item["seed"],
        "summary": _question_summary(payload_json),
        "context_kind": "generic",
        "instruction": "",
        "context_lines": [],
        "pairs": [],
        "numbers": [],
        "words": [],
        "shapes": {},
        "question_text": "",
        "options": [],
        "correct_answer": "",
    }

    try:
        payload = json.loads(payload_json)
        correct_answer = json.loads(correct_answer_json).get("answer", "")
    except json.JSONDecodeError:
        return preview

    prompt = payload.get("prompt", {})
    options = [str(option) for option in payload.get("options", [])]
    preview["correct_answer"] = str(correct_answer)

    if section_type == SectionType.REASONING:
        preview.update(
            {
                "context_kind": "statements",
                "context_lines": prompt.get("statements", []),
                "question_text": prompt.get("question", "Choose one answer."),
                "options": options,
            }
        )
        return preview

    if section_type == SectionType.PERCEPTUAL_SPEED:
        preview.update(
            {
                "context_kind": "pairs",
                "instruction": prompt.get("instruction", ""),
                "pairs": prompt.get("pairs", []),
                "question_text": "How many matching pairs are there?",
                "reveal_mode": "context_then_question",
                "options": options,
            }
        )
        return preview

    if section_type == SectionType.NUMBER_SPEED_ACCURACY:
        preview.update(
            {
                "context_kind": "numbers",
                "instruction": prompt.get("instruction", ""),
                "numbers": prompt.get("numbers", []),
                "question_text": prompt.get("instruction", "Choose one answer."),
                "reveal_mode": "question_only",
                "options": options,
            }
        )
        return preview

    if section_type == SectionType.WORD_MEANING:
        preview.update(
            {
                "context_kind": "words",
                "instruction": prompt.get("instruction", ""),
                "words": prompt.get("words", []),
                "question_text": prompt.get("instruction", "Choose one answer."),
                "reveal_mode": "question_only",
                "options": options,
            }
        )
        return preview

    if section_type == SectionType.SPATIAL_VISUALIZATION:
        preview.update(
            {
                "context_kind": "letter_pairs",
                "instruction": prompt.get("instruction", ""),
                "letter_pairs": prompt.get("letter_pairs", []),
                "question_text": "How many pairs show the same image?",
                "options": options,
            }
        )
        return preview

    if section_type in {SectionType.CCAT_NUMERICAL, SectionType.CCAT_VERBAL, SectionType.CCAT_SPATIAL}:
        preview.update(
            {
                "context_kind": "generic",
                "instruction": prompt.get("instruction", ""),
                "question_text": prompt.get("question", prompt.get("instruction", "Choose one answer.")),
                "reveal_mode": "question_only",
                "options": options,
            }
        )
        return preview

    return preview


def _build_generated_preview(item: dict) -> dict:
    payload = item.get("payload", {})
    prompt = payload.get("prompt", {})
    options = [str(option) for option in payload.get("options", [])]
    correct_answer = str(item.get("correct_answer", {}).get("answer", ""))
    section_type = item.get("section_type", "")

    preview = {
        "seed": item.get("seed", ""),
        "summary": prompt.get("question") or prompt.get("instruction", "Question preview unavailable."),
        "context_kind": "generic",
        "instruction": "",
        "context_lines": [],
        "pairs": [],
        "numbers": [],
        "words": [],
        "shapes": {},
        "question_text": "",
        "options": options,
        "correct_answer": correct_answer,
        "reveal_mode": "context_then_question",
    }

    if section_type == SectionType.REASONING:
        preview.update(
            {
                "context_kind": "statements",
                "context_lines": prompt.get("statements", []),
                "question_text": prompt.get("question", "Choose one answer."),
            }
        )
        return preview

    if section_type == SectionType.PERCEPTUAL_SPEED:
        preview.update(
            {
                "context_kind": "pairs",
                "instruction": prompt.get("instruction", ""),
                "pairs": prompt.get("pairs", []),
                "question_text": "How many matching pairs are there?",
            }
        )
        return preview

    if section_type == SectionType.NUMBER_SPEED_ACCURACY:
        preview.update(
            {
                "context_kind": "numbers",
                "instruction": prompt.get("instruction", ""),
                "numbers": prompt.get("numbers", []),
                "question_text": prompt.get("instruction", "Choose one answer."),
                "reveal_mode": "question_only",
            }
        )
        return preview

    if section_type == SectionType.WORD_MEANING:
        preview.update(
            {
                "context_kind": "words",
                "instruction": prompt.get("instruction", ""),
                "words": prompt.get("words", []),
                "question_text": prompt.get("instruction", "Choose one answer."),
                "reveal_mode": "question_only",
            }
        )
        return preview

    if section_type == SectionType.SPATIAL_VISUALIZATION:
        preview.update(
            {
                "context_kind": "letter_pairs",
                "instruction": prompt.get("instruction", ""),
                "letter_pairs": prompt.get("letter_pairs", []),
                "question_text": "How many pairs show the same image?",
            }
        )
        return preview

    if section_type in {SectionType.CCAT_NUMERICAL, SectionType.CCAT_VERBAL, SectionType.CCAT_SPATIAL}:
        preview.update(
            {
                "context_kind": "generic",
                "instruction": prompt.get("instruction", ""),
                "question_text": prompt.get("question", prompt.get("instruction", "Choose one answer.")),
                "reveal_mode": "question_only",
            }
        )
        return preview

    return preview
