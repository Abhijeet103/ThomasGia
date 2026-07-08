from __future__ import annotations

import logging
from dataclasses import asdict

from allauth.account.forms import LoginForm
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.http import Http404
from django.shortcuts import redirect, render
from django.views.generic import TemplateView
from django.db.models import Prefetch
from django.views import View

from backend.apps.billing.services import build_plan_cards, sync_user_subscription_access
from backend.apps.assessments.models import AttemptMode, AttemptSection, AttemptStatus, SectionProgress, SectionType
from backend.apps.assessments.services import (
    FullTestSessionError,
    SECTION_TIME_LIMITS,
    can_start_attempt,
    expire_stale_attempts,
    get_or_create_full_test_attempt,
    get_or_create_section_attempt,
    serialize_full_test_attempt_for_frontend,
)
from prepgia.generators import generate_question
from prepgia.preview_data import get_questions
from prepgia.schema import DEFAULT_DB_PATH, get_connection


SECTION_META = {
    SectionType.REASONING: {
        "title": "Reasoning",
        "description": "Comparative and transitive logic questions under timed conditions.",
    },
    SectionType.PERCEPTUAL_SPEED: {
        "title": "Perceptual Speed",
        "description": "Fast letter-pair matching built to simulate GIA-style pressure.",
    },
    SectionType.NUMBER_SPEED_ACCURACY: {
        "title": "Number Speed & Accuracy",
        "description": "Find the number furthest from the median with speed and accuracy.",
    },
    SectionType.WORD_MEANING: {
        "title": "Word Meaning",
        "description": "Odd-one-out vocabulary sets backed by a curated word bank.",
    },
    SectionType.SPATIAL_VISUALIZATION: {
        "title": "Spatial Visualization",
        "description": "Decide whether abstract shapes are rotated matches or mirrored variants.",
    },
}

SECTION_INSTRUCTIONS = {
    SectionType.REASONING: "Read the context statements first. Once you understand the relationship, reveal the question and choose the correct person or thing.",
    SectionType.PERCEPTUAL_SPEED: "Look at the letter pairs carefully. Count the matching pairs quickly before selecting the correct number.",
    SectionType.NUMBER_SPEED_ACCURACY: "Review the three numbers, identify the middle value mentally, and choose the number furthest from it.",
    SectionType.WORD_MEANING: "Read the words shown in the context, spot the odd one out, and then choose it from the answer options.",
    SectionType.SPATIAL_VISUALIZATION: "Study the shapes first, then decide whether they are the same when rotated or if one is mirrored.",
}

SECTION_VIDEO_PLACEHOLDERS = {
    SectionType.REASONING: {"title": "Reasoning walkthrough", "duration": "04:12"},
    SectionType.PERCEPTUAL_SPEED: {"title": "Perceptual speed walkthrough", "duration": "03:05"},
    SectionType.NUMBER_SPEED_ACCURACY: {"title": "Number speed walkthrough", "duration": "03:48"},
    SectionType.WORD_MEANING: {"title": "Word meaning walkthrough", "duration": "02:56"},
    SectionType.SPATIAL_VISUALIZATION: {"title": "Spatial walkthrough", "duration": "04:20"},
}

SECTION_PRACTICE_GENERATION_COUNT = 40
logger = logging.getLogger(__name__)


class HomePageView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_questions = get_questions()
        context.update(
            {
                "page_title": "PrepGIA | Thomas GIA Practice Platform",
                "meta_description": "Timed Thomas GIA practice tests with full mocks, section-wise drills, Google login, and subscription paywall support.",
                "question_count": len(all_questions),
                "sections": _section_cards(),
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
                "page_title": "Pricing | PrepGIA",
                "meta_description": "View free and paid plans for PrepGIA practice tests.",
                "active_subscription": active_subscription,
                "plans": build_plan_cards(self.request.user, active_subscription),
            }
        )
        return context


class SubscriptionPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/subscription.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sync_user_subscription_access(self.request.user)
        active_subscription = self.request.user.subscriptions.filter(status="active").order_by("-updated_at").first()
        context.update(
            {
                "page_title": "Subscription | PrepGIA",
                "meta_description": "View your PrepGIA subscription status and manage cancellation.",
                "active_subscription": active_subscription,
                "subscription_expires_at": self.request.user.subscription_expires_at,
                "plans": build_plan_cards(self.request.user, active_subscription),
                "checkout_state": self.request.GET.get("checkout", ""),
            }
        )
        return context


class PracticePageView(TemplateView):
    template_name = "pages/practice.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Practice Tests | PrepGIA",
                "meta_description": "Choose full test or section-wise Thomas GIA practice modes.",
                "sections": _practice_section_cards(self.request),
            }
        )
        return context


class SectionsPageView(TemplateView):
    template_name = "pages/sections.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        sections = []
        for key, meta in SECTION_META.items():
            sections.append(
                {
                    "key": key,
                    "title": meta["title"],
                    "description": meta["description"],
                    "time_limit_seconds": SECTION_TIME_LIMITS[key],
                    "sample_count": len(get_questions(key)),
                }
            )
        context.update(
            {
                "page_title": "Sections | PrepGIA",
                "meta_description": "Browse all five Thomas GIA-style sections available in PrepGIA.",
                "sections": sections,
            }
        )
        return context


class FullTestPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/full_test.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        full_test_data = []
        full_test_attempt_id = None
        access_error = None
        try:
            attempt = get_or_create_full_test_attempt(self.request.user)
            full_test_attempt_id = attempt.id
            full_test_data = serialize_full_test_attempt_for_frontend(attempt, SECTION_META, SECTION_INSTRUCTIONS)
        except PermissionError as exc:
            access_error = str(exc)
        except FullTestSessionError:
            logger.exception("Full test setup failed because the active Redis-backed session was unavailable.")
            access_error = "Full test is temporarily unavailable. Please try again in a moment."
        context.update(
            {
                "page_title": "Full Test | PrepGIA",
                "meta_description": "Run through all PrepGIA sections in one full guided flow with practice and timed test phases.",
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
        slug = kwargs["slug"]
        try:
            section_type = SectionType(slug)
        except ValueError as exc:
            raise Http404("Section not found.") from exc

        mode = self.request.GET.get("mode", "practice")
        if mode not in {"practice", "test"}:
            mode = "practice"

        meta = SECTION_META[section_type]
        section_attempt_id = None
        section_submit_url = ""
        if mode == "test" and self.request.user.is_authenticated:
            attempt = get_or_create_section_attempt(self.request.user, section_type)
            section_attempt_id = attempt.id
            attempt_section = next(iter(attempt.sections.all()), None)
            previews = [_build_generated_preview(item) for item in (attempt_section.question_payload if attempt_section else [])]
            section_submit_url = f"/api/tests/section-tests/{section_attempt_id}/submit/" if section_attempt_id else ""
        else:
            previews = _build_section_questions(section_type, mode)
        context.update(
            {
                "page_title": f"{meta['title']} {mode.title()} | PrepGIA",
                "meta_description": meta["description"],
                "section": {
                    "key": section_type,
                    "title": meta["title"],
                    "description": meta["description"],
                    "instruction": SECTION_INSTRUCTIONS[section_type],
                    "time_limit_seconds": SECTION_TIME_LIMITS[section_type],
                    "previews": previews,
                    "mode": mode,
                    "video": SECTION_VIDEO_PLACEHOLDERS[section_type],
                    "attempt_id": section_attempt_id,
                    "submit_url": section_submit_url,
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
            "page_title": "Login | PrepGIA",
            "meta_description": "Sign in to PrepGIA with email and password or continue with Google.",
            "google_login_path": "/accounts/google/login/",
            "form": form,
            "next_value": request.GET.get("next", ""),
        }


class DashboardPageView(LoginRequiredMixin, TemplateView):
    template_name = "pages/dashboard.html"
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        expired_count = expire_stale_attempts(self.request.user)
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
        recent_attempts = attempts[:10]
        active_attempts = [attempt for attempt in attempts if attempt.status in {AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS}]
        full_test_attempts = [attempt for attempt in attempts if attempt.mode == AttemptMode.FULL_TEST and attempt.status == "completed"][:10]
        section_attempts = [attempt for attempt in attempts if attempt.mode == AttemptMode.SECTION and attempt.status == "completed"][:20]
        active_subscription = self.request.user.subscriptions.filter(status="active").first()
        full_test_decision = can_start_attempt(self.request.user, AttemptMode.FULL_TEST)

        active_attempt_rows = []
        for attempt in active_attempts:
            first_section = next(iter(attempt.sections.all()), None)
            section_title = SECTION_META[first_section.section_type]["title"] if first_section else "-"
            continue_url = reverse("pages:full-test") if attempt.mode == AttemptMode.FULL_TEST else ""
            if attempt.mode == AttemptMode.SECTION and first_section:
                continue_url = f"{reverse('pages:section-detail', args=[first_section.section_type])}?mode=test"
            active_attempt_rows.append(
                {
                    "attempt_id": attempt.id,
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
            recent_attempt_rows.append(
                {
                    "attempt_id": attempt.id,
                    "mode_label": attempt.get_mode_display(),
                    "section_title": SECTION_META[first_section.section_type]["title"] if first_section else "-",
                    "status_label": attempt.get_status_display(),
                    "score": attempt.overall_adjusted_score,
                    "started_at": attempt.started_at,
                    "completed_at": attempt.completed_at,
                }
            )

        section_score_rows = []
        for attempt in section_attempts:
            section = next(iter(attempt.sections.all()), None)
            if section is None:
                continue
            section_score_rows.append(
                {
                    "attempt_id": attempt.id,
                    "section_title": SECTION_META[section.section_type]["title"],
                    "score": section.adjusted_score,
                    "question_count": section.question_count,
                    "time_limit_seconds": section.time_limit_seconds,
                    "completed_at": attempt.completed_at,
                }
            )

        full_test_rows = []
        for attempt in full_test_attempts:
            section_scores = {section.section_type: section.adjusted_score for section in attempt.sections.all()}
            full_test_rows.append(
                {
                    "attempt_id": attempt.id,
                    "completed_at": attempt.completed_at,
                    "overall_score": attempt.overall_adjusted_score,
                    "ordered_section_scores": [section_scores.get(key, "-") for key in SECTION_META],
                }
            )

        context.update(
            {
                "page_title": "Dashboard | PrepGIA",
                "meta_description": "Track your PrepGIA access, attempts, and progress.",
                "active_attempt_rows": active_attempt_rows,
                "attempts": recent_attempt_rows,
                "full_test_rows": full_test_rows,
                "section_score_rows": section_score_rows,
                "active_subscription": active_subscription,
                "full_test_decision": full_test_decision,
                "section_score_headers": [SECTION_META[key]["title"] for key in SECTION_META],
                "subscription_expires_at": self.request.user.subscription_expires_at,
                "expired_attempt_count": expired_count,
            }
        )
        return context


def _section_cards():
    return [
        {"key": key, "title": meta["title"], "description": meta["description"], "sample_count": len(get_questions(key))}
        for key, meta in SECTION_META.items()
    ]


def _practice_section_cards(request):
    progress_by_section = {}
    active_attempts = {}
    if request.user.is_authenticated:
        progress_by_section = {
            item.section_type: item
            for item in SectionProgress.objects.filter(user=request.user)
        }
        for attempt in (
            request.user.attempts.filter(mode=AttemptMode.SECTION, status__in=[AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS])
            .prefetch_related(
                Prefetch("sections", queryset=AttemptSection.objects.order_by("order_index"))
            )
            .order_by("-started_at")
        ):
            first_section = next(iter(attempt.sections.all()), None)
            if first_section and first_section.section_type not in active_attempts:
                active_attempts[first_section.section_type] = attempt

    cards = []
    for index, (key, meta) in enumerate(SECTION_META.items()):
        progress = progress_by_section.get(key)
        practice_solved = progress.practice_questions_solved if progress else 0
        tests_taken = progress.tests_taken if progress else 0
        active_attempt = active_attempts.get(key)
        practice_goal = 40
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

        cards.append(
            {
                "key": key,
                "title": meta["title"],
                "description": meta["description"],
                "question_count": SECTION_PRACTICE_GENERATION_COUNT,
                "duration_minutes": max(1, SECTION_TIME_LIMITS[key] // 60),
                "practice_solved": practice_solved,
                "tests_taken": tests_taken,
                "progress_percent": progress_percent,
                "status_label": status_label,
                "status_class": status_class,
                "action_label": "Resume" if (active_attempt or practice_solved > 0 or tests_taken > 0) else "Start",
                "action_url": f"{reverse('pages:section-detail', args=[key])}?mode={'test' if active_attempt else 'practice'}",
                "theme_class": f"section-theme-{index % 3}",
            }
        )
    return cards


def _build_section_questions(section_type: str, mode: str) -> list[dict]:
    difficulty = "easy" if mode == "practice" else "medium"
    question_count = SECTION_PRACTICE_GENERATION_COUNT if mode == "practice" else SECTION_TIME_LIMITS[section_type]
    conn = get_connection(DEFAULT_DB_PATH)
    try:
        questions = []
        for index in range(question_count):
            seed = f"section:{section_type}:{mode}:{difficulty}:{index}"
            generated = generate_question(section_type, difficulty, seed, conn=conn)
            questions.append(_build_generated_preview(asdict(generated)))
        return questions
    finally:
        conn.close()


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
                "context_kind": "shapes",
                "instruction": prompt.get("instruction", ""),
                "shapes": {
                    "shape_a": prompt.get("shape_a", {}),
                    "shape_b": prompt.get("shape_b", {}),
                },
                "question_text": prompt.get("instruction", "Choose one answer."),
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
                "context_kind": "shapes",
                "instruction": prompt.get("instruction", ""),
                "shapes": {
                    "shape_a": prompt.get("shape_a", {}),
                    "shape_b": prompt.get("shape_b", {}),
                },
                "question_text": prompt.get("instruction", "Choose one answer."),
            }
        )
        return preview

    return preview
