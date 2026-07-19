from __future__ import annotations

import json
import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from backend.apps.assessments.config import ASSESSMENT_CONFIG, ASSESSMENT_PREPGIA
from .models import Attempt, AttemptMode, AttemptStatus, SectionType
from .services import (
    SECTION_TIME_LIMITS,
    FullTestSessionError,
    can_start_attempt,
    complete_attempt_with_zero,
    create_attempt,
    expire_stale_attempts,
    get_full_test_question,
    record_practice_progress,
    submit_section_attempt,
    submit_full_test_attempt,
)


logger = logging.getLogger(__name__)


class SectionCatalogView(View):
    def get(self, request):
        return JsonResponse(
            {
                "sections": [
                    {
                        "key": module["key"],
                        "label": module["title"],
                        "assessment_type": assessment_type,
                        "time_limit_seconds": SECTION_TIME_LIMITS[module["key"]],
                        "available_in_section_mode": True,
                    }
                    for assessment_type, config in ASSESSMENT_CONFIG.items()
                    for module in config["modules"]
                ],
                "rules": {
                    "default_user_role": "free",
                    "free_full_test_limit": 1,
                    "section_wise_tests_enabled": True,
                },
            }
        )


@method_decorator(csrf_exempt, name="dispatch")
class AttemptStartView(View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({"detail": "Authentication required."}, status=401)

        payload = json.loads(request.body or "{}")
        mode = payload.get("mode", AttemptMode.SECTION)
        difficulty = payload.get("difficulty", "easy")
        assessment_type = payload.get("assessment_type", ASSESSMENT_PREPGIA)
        section_type = payload.get("section_type")

        if mode == AttemptMode.SECTION and section_type not in {choice for choice, _ in SectionType.choices}:
            return JsonResponse({"detail": "Valid section_type is required for a section-wise test."}, status=400)

        logger.info(
            "Attempt start requested user_id=%s assessment_type=%s mode=%s difficulty=%s section_type=%s",
            request.user.id,
            assessment_type,
            mode,
            difficulty,
            section_type or "n/a",
        )
        access = can_start_attempt(request.user, mode, assessment_type=assessment_type)
        if not access.allowed:
            logger.warning("Attempt start denied user_id=%s mode=%s reason=%s", request.user.id, mode, access.message)
            return JsonResponse({"detail": access.message}, status=403)

        attempt = create_attempt(
            request.user,
            mode,
            difficulty=difficulty,
            section_type=section_type,
            assessment_type=assessment_type,
        )
        logger.info("Attempt start completed user_id=%s attempt_id=%s assessment_type=%s mode=%s", request.user.id, attempt.id, assessment_type, mode)
        return JsonResponse(
            {
                "attempt_id": attempt.id,
                "assessment_type": attempt.assessment_type,
                "mode": attempt.mode,
                "status": attempt.status,
                "sections": [
                    {
                        "id": section.id,
                        "section_type": section.section_type,
                        "question_count": section.question_count,
                        "time_limit_seconds": section.time_limit_seconds,
                    }
                    for section in attempt.sections.all().order_by("order_index")
                ],
            },
            status=201,
        )


@method_decorator(csrf_exempt, name="dispatch")
class FullTestSubmitView(LoginRequiredMixin, View):
    def post(self, request, attempt_id: int):
        expire_stale_attempts(request.user)
        attempt = Attempt.objects.filter(id=attempt_id, user=request.user, mode=AttemptMode.FULL_TEST).first()
        if attempt is None:
            return JsonResponse({"detail": "Attempt not found."}, status=404)

        payload = json.loads(request.body or "{}")
        logger.info("Full test submit requested attempt_id=%s user_id=%s", attempt_id, request.user.id)
        try:
            result = submit_full_test_attempt(attempt, payload.get("sections", []))
        except FullTestSessionError:
            logger.exception("Full test submission failed because the active Redis-backed session was unavailable.")
            return JsonResponse({"detail": "Full test session is temporarily unavailable. Please restart the test."}, status=503)
        logger.info("Full test submit completed attempt_id=%s user_id=%s overall_score=%s", attempt_id, request.user.id, result["overall_score"])
        return JsonResponse(result)


class FullTestQuestionView(LoginRequiredMixin, View):
    def get(self, request, attempt_id: int):
        expire_stale_attempts(request.user)
        attempt = Attempt.objects.filter(id=attempt_id, user=request.user, mode=AttemptMode.FULL_TEST).first()
        if attempt is None:
            return JsonResponse({"detail": "Attempt not found."}, status=404)

        if attempt.status == AttemptStatus.COMPLETED:
            return JsonResponse({"detail": "This test is already completed."}, status=409)

        try:
            section_index = int(request.GET.get("section_index", "-1"))
            question_index = int(request.GET.get("question_index", "-1"))
        except ValueError:
            return JsonResponse({"detail": "Question indexes must be integers."}, status=400)

        phase = request.GET.get("phase", "")
        logger.info(
            "Full test question requested attempt_id=%s user_id=%s section_index=%s phase=%s question_index=%s",
            attempt_id,
            request.user.id,
            section_index,
            phase,
            question_index,
        )
        try:
            question = get_full_test_question(attempt, section_index, phase, question_index)
        except FullTestSessionError:
            logger.exception("Full test question load failed because the active Redis-backed session was unavailable.")
            return JsonResponse({"detail": "Full test session is temporarily unavailable. Please restart the test."}, status=503)
        return JsonResponse(question)


class AttemptEndView(LoginRequiredMixin, View):
    def post(self, request, attempt_id: int):
        attempt = Attempt.objects.filter(id=attempt_id, user=request.user).prefetch_related("sections").first()
        if attempt is None:
            return redirect("pages:dashboard")

        if attempt.status in {AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS}:
            complete_attempt_with_zero(attempt, reason="manual_end")
            logger.info("Attempt manually ended attempt_id=%s user_id=%s", attempt.id, request.user.id)

        return redirect("pages:dashboard")


@method_decorator(csrf_exempt, name="dispatch")
class SectionTestSubmitView(LoginRequiredMixin, View):
    def post(self, request, attempt_id: int):
        expire_stale_attempts(request.user)
        attempt = Attempt.objects.filter(id=attempt_id, user=request.user, mode=AttemptMode.SECTION).prefetch_related("sections").first()
        if attempt is None:
            return JsonResponse({"detail": "Attempt not found."}, status=404)

        payload = json.loads(request.body or "{}")
        logger.info("Section test submit requested attempt_id=%s user_id=%s", attempt_id, request.user.id)
        result = submit_section_attempt(attempt, payload.get("answers", []))
        return JsonResponse(result)


@method_decorator(csrf_exempt, name="dispatch")
class PracticeProgressUpdateView(LoginRequiredMixin, View):
    def post(self, request):
        payload = json.loads(request.body or "{}")
        section_type = payload.get("section_type")
        assessment_type = payload.get("assessment_type", ASSESSMENT_PREPGIA)
        if section_type not in {choice for choice, _ in SectionType.choices}:
            return JsonResponse({"detail": "Valid section_type is required."}, status=400)

        solved_increment = int(payload.get("solved_increment", 1) or 1)
        progress = record_practice_progress(
            request.user,
            section_type,
            solved_increment=solved_increment,
            assessment_type=assessment_type,
        )
        return JsonResponse(
            {
                "assessment_type": assessment_type,
                "section_type": section_type,
                "practice_questions_solved": progress.practice_questions_solved,
                "tests_taken": progress.tests_taken,
            }
        )
