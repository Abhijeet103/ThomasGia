from __future__ import annotations

import json
import logging
from datetime import timedelta
from dataclasses import asdict, dataclass
from typing import Any

from django.conf import settings
from django.utils import timezone
from redis import Redis
from redis.exceptions import RedisError

from backend.apps.accounts.models import User, UserRole
from backend.apps.assessments.config import (
    ASSESSMENT_PREPGIA,
    get_assessment_config,
    get_assessment_module_keys,
    get_module_assessment_type,
    get_time_limit_seconds,
)
from prepgia.generators import SECTION_TYPES, generate_question

from .models import Attempt, AttemptAnswer, AttemptMode, AttemptSection, AttemptStatus, SectionProgress, SectionType

ACTIVE_ATTEMPT_EXPIRY_SECONDS = 2 * 60 * 60
_redis_client: Redis | None = None
logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    allowed: bool
    message: str


class FullTestSessionError(Exception):
    pass


FREE_FULL_TEST_LIMIT = 1
FREE_SECTION_TEST_LIMIT = 2
FREE_PRACTICE_QUESTION_LIMIT = 10


SECTION_TIME_LIMITS = {section_type: get_time_limit_seconds(section_type) for section_type in SECTION_TYPES}

def can_start_attempt(user: User, mode: str, assessment_type: str = ASSESSMENT_PREPGIA) -> AccessDecision:
    if user.role == UserRole.PAID:
        return AccessDecision(True, "")

    if mode == AttemptMode.FULL_TEST:
        used = Attempt.objects.filter(user=user, mode=AttemptMode.FULL_TEST, assessment_type=assessment_type).count()
        if used >= FREE_FULL_TEST_LIMIT:
            return AccessDecision(False, f"Free users can take up to {FREE_FULL_TEST_LIMIT} full test. Upgrade to unlock unlimited access.")
        remaining = FREE_FULL_TEST_LIMIT - used
        return AccessDecision(True, f"Free tier: {remaining} full test remaining.")

    if mode == AttemptMode.SECTION:
        used = Attempt.objects.filter(user=user, mode=AttemptMode.SECTION, assessment_type=assessment_type).count()
        if used >= FREE_SECTION_TEST_LIMIT:
            return AccessDecision(False, f"Free users can take up to {FREE_SECTION_TEST_LIMIT} module tests. Upgrade to unlock unlimited access.")
        remaining = FREE_SECTION_TEST_LIMIT - used
        return AccessDecision(True, f"Free tier: {remaining} module test(s) remaining.")

    return AccessDecision(True, "")


def create_attempt(
    user: User,
    mode: str,
    difficulty: str = "easy",
    section_type: str | None = None,
    assessment_type: str = ASSESSMENT_PREPGIA,
) -> Attempt:
    decision = can_start_attempt(user, mode, assessment_type=assessment_type)
    if not decision.allowed:
        raise PermissionError(decision.message)

    attempt = Attempt.objects.create(
        user=user,
        assessment_type=assessment_type,
        mode=mode,
        status=AttemptStatus.IN_PROGRESS,
    )
    section_keys = [section_type] if mode == AttemptMode.SECTION and section_type else get_assessment_module_keys(assessment_type)
    logger.info(
        "Creating attempt id=%s user_id=%s assessment_type=%s mode=%s difficulty=%s section_type=%s section_count=%s",
        attempt.id,
        user.id,
        assessment_type,
        mode,
        difficulty,
        section_type or "all",
        len(section_keys),
    )
    for index, section_key in enumerate(section_keys):
        question_target = get_time_limit_seconds(section_key) if mode == AttemptMode.SECTION else 5
        logger.info(
            "Generating section attempt payload attempt_id=%s section=%s difficulty=%s question_count=%s",
            attempt.id,
            section_key,
            difficulty,
            question_target,
        )
        payloads: list[dict[str, Any]] = []
        for question_index in range(question_target):
            seed = f"{attempt.id}:{section_key}:{difficulty}:{question_index}"
            generated = generate_question(section_key, difficulty, seed)
            payloads.append(asdict(generated))

        AttemptSection.objects.create(
            attempt=attempt,
            section_type=section_key,
            order_index=index,
            difficulty=difficulty,
            time_limit_seconds=get_time_limit_seconds(section_key),
            question_count=len(payloads),
            question_payload=payloads,
        )
        logger.info(
            "Saved section attempt payload to DB attempt_id=%s section=%s order_index=%s question_count=%s",
            attempt.id,
            section_key,
            index,
            len(payloads),
        )

    logger.info("Attempt created successfully attempt_id=%s user_id=%s mode=%s", attempt.id, user.id, mode)
    return attempt


def get_or_create_full_test_attempt(user: User, assessment_type: str = ASSESSMENT_PREPGIA) -> Attempt:
    decision = can_start_attempt(user, AttemptMode.FULL_TEST, assessment_type=assessment_type)
    if not decision.allowed:
        raise PermissionError(decision.message)
    assessment_config = get_assessment_config(assessment_type)
    full_test_practice_count = assessment_config["full_test_practice_count"]
    attempt = Attempt.objects.create(
        user=user,
        assessment_type=assessment_type,
        mode=AttemptMode.FULL_TEST,
        status=AttemptStatus.IN_PROGRESS,
    )
    logger.info("Created new full test attempt_id=%s user_id=%s assessment_type=%s", attempt.id, user.id, assessment_type)

    session_sections = []
    existing_sections = {section.section_type: section for section in attempt.sections.all()}
    for index, section_key in enumerate(get_assessment_module_keys(assessment_type)):
        logger.info(
            "Generating full test section attempt_id=%s section=%s practice_count=%s test_count=%s",
            attempt.id,
            section_key,
            full_test_practice_count,
            get_time_limit_seconds(section_key),
        )
        practice_questions = _build_question_batch(attempt.id, section_key, "practice", full_test_practice_count, "easy")
        test_count = get_time_limit_seconds(section_key)
        test_questions = _build_question_batch(attempt.id, section_key, "test", test_count, "medium")

        section = existing_sections.get(section_key)
        if section is None:
            section = AttemptSection.objects.create(
                attempt=attempt,
                section_type=section_key,
                order_index=index,
                difficulty="mixed",
                time_limit_seconds=get_time_limit_seconds(section_key),
                question_count=len(test_questions),
                question_payload={},
            )
        else:
            section.order_index = index
            section.difficulty = "mixed"
            section.time_limit_seconds = get_time_limit_seconds(section_key)
            section.question_count = len(test_questions)
            section.question_payload = {}
            section.save(update_fields=["order_index", "difficulty", "time_limit_seconds", "question_count", "question_payload"])
            logger.info(
                "Updated full test section metadata in DB attempt_id=%s section_id=%s section=%s test_count=%s",
                attempt.id,
                section.id,
                section_key,
                len(test_questions),
            )

        session_sections.append(
            {
                "section_id": section.id,
                "section_type": section_key,
                "practice_questions": practice_questions,
                "test_questions": test_questions,
            }
        )

    _save_full_test_session(
        attempt.id,
        {
            "attempt_id": attempt.id,
            "user_id": user.id,
            "sections": session_sections,
            "created_at": timezone.now().isoformat(),
        },
    )
    logger.info(
        "Exported full test session to Redis attempt_id=%s user_id=%s section_count=%s redis_url=%s",
        attempt.id,
        user.id,
        len(session_sections),
        settings.REDIS_URL,
    )
    return attempt


def get_or_create_section_attempt(
    user: User,
    section_type: str,
    difficulty: str = "medium",
    assessment_type: str | None = None,
) -> Attempt:
    resolved_assessment_type = assessment_type or get_module_assessment_type(section_type)
    expire_stale_attempts(user)
    active_attempt = (
        Attempt.objects.filter(
            user=user,
            assessment_type=resolved_assessment_type,
            mode=AttemptMode.SECTION,
            status__in=[AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS],
            sections__section_type=section_type,
        )
        .prefetch_related("sections")
        .order_by("-started_at")
        .first()
    )
    if active_attempt is not None:
        logger.info("Reusing active section attempt attempt_id=%s user_id=%s section=%s", active_attempt.id, user.id, section_type)
        return active_attempt

    attempt = create_attempt(
        user,
        AttemptMode.SECTION,
        difficulty=difficulty,
        section_type=section_type,
        assessment_type=resolved_assessment_type,
    )
    logger.info("Created new section attempt attempt_id=%s user_id=%s section=%s", attempt.id, user.id, section_type)
    return attempt


def serialize_full_test_attempt_for_frontend(
    attempt: Attempt,
    section_meta: dict[str, dict[str, str]],
    instructions: dict[str, str],
    full_test_practice_count: int,
) -> list[dict[str, Any]]:
    payload = []
    for section in attempt.sections.order_by("order_index"):
        payload.append(
            {
                "section_id": section.id,
                "key": section.section_type,
                "title": section_meta[section.section_type]["title"],
                "description": section_meta[section.section_type]["description"],
                "instruction": instructions[section.section_type],
                "time_limit_seconds": section.time_limit_seconds,
                "practice_count": full_test_practice_count,
                "test_count": section.question_count,
            }
        )
    return payload


def get_full_test_question(attempt: Attempt, section_index: int, phase: str, question_index: int) -> dict[str, Any]:
    session = _load_full_test_session(attempt.id)
    sections = session.get("sections", [])
    if section_index < 0 or section_index >= len(sections):
        raise FullTestSessionError("Invalid section index.")
    if phase not in {"practice", "test"}:
        raise FullTestSessionError("Invalid phase.")
    if question_index < 0:
        raise FullTestSessionError("Invalid question index.")

    section = sections[section_index]
    question_set = section["practice_questions"] if phase == "practice" else section["test_questions"]
    if question_index >= len(question_set):
        raise FullTestSessionError("Question index is out of range.")

    question = question_set[question_index]
    logger.info(
        "Serving full test question attempt_id=%s user_id=%s section_index=%s section=%s phase=%s question_index=%s",
        attempt.id,
        attempt.user_id,
        section_index,
        section.get("section_type"),
        phase,
        question_index,
    )
    return _serialize_generated_question_for_player(question, include_correct_answer=phase == "practice")


def submit_full_test_attempt(attempt: Attempt, submitted_answers: list[dict[str, Any]]) -> dict[str, Any]:
    if attempt.status == AttemptStatus.COMPLETED:
        logger.info("Full test submission reused completed result attempt_id=%s user_id=%s", attempt.id, attempt.user_id)
        return {
            "attempt_id": attempt.id,
            "overall_score": attempt.overall_adjusted_score,
            "section_scores": [
                {"section_type": section.section_type, "score": section.adjusted_score}
                for section in attempt.sections.order_by("order_index")
            ],
        }

    logger.info(
        "Submitting full test attempt_id=%s user_id=%s submitted_section_count=%s",
        attempt.id,
        attempt.user_id,
        len(submitted_answers),
    )
    session = _load_full_test_session(attempt.id)
    session_sections = {
        item["section_id"]: item
        for item in session.get("sections", [])
    }
    submitted_by_section = {item["section_id"]: item.get("answers", []) for item in submitted_answers}
    AttemptAnswer.objects.filter(attempt_section__attempt=attempt).delete()
    logger.info("Cleared previous saved answers for attempt_id=%s", attempt.id)

    total_score = 0
    section_scores = []
    for section in attempt.sections.order_by("order_index"):
        session_section = session_sections.get(section.id)
        if session_section is None:
            raise FullTestSessionError("Active test session is missing section data.")
        expected_questions = session_section.get("test_questions", [])
        answers_by_index = {
            item["question_index"]: str(item.get("selected_option", ""))
            for item in submitted_by_section.get(section.id, [])
        }

        section_score = 0
        for question_index, question in enumerate(expected_questions):
            correct_answer = str(question.get("correct_answer", ""))
            selected_answer = answers_by_index.get(question_index, "")
            is_correct = selected_answer == correct_answer
            if is_correct:
                section_score += 1
            AttemptAnswer.objects.create(
                attempt_section=section,
                question_index=question_index,
                user_answer={"selected_option": selected_answer},
                is_correct=is_correct,
                penalty_applied=0,
            )

        section.adjusted_score = section_score
        section.question_payload = {}
        section.save(update_fields=["adjusted_score", "question_payload"])
        logger.info(
            "Saved section score to DB attempt_id=%s section_id=%s section=%s score=%s question_count=%s",
            attempt.id,
            section.id,
            section.section_type,
            section_score,
            len(expected_questions),
        )
        section_scores.append({"section_type": section.section_type, "score": section_score})
        total_score += section_score
        record_test_progress(attempt.user, section.section_type, section_score)

    attempt.overall_adjusted_score = total_score
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["overall_adjusted_score", "status", "completed_at"])
    logger.info(
        "Saved full test result to DB attempt_id=%s user_id=%s total_score=%s section_count=%s",
        attempt.id,
        attempt.user_id,
        total_score,
        len(section_scores),
    )
    _delete_full_test_session(attempt.id)

    return {
        "attempt_id": attempt.id,
        "overall_score": total_score,
        "section_scores": section_scores,
    }


def submit_section_attempt(attempt: Attempt, submitted_answers: list[dict[str, Any]]) -> dict[str, Any]:
    if attempt.status == AttemptStatus.COMPLETED:
        section = attempt.sections.order_by("order_index").first()
        return {
            "attempt_id": attempt.id,
            "overall_score": attempt.overall_adjusted_score,
            "section_score": section.adjusted_score if section else attempt.overall_adjusted_score,
        }

    section = attempt.sections.order_by("order_index").first()
    if section is None:
        raise FullTestSessionError("Section attempt is missing section data.")

    logger.info(
        "Submitting section attempt attempt_id=%s user_id=%s section=%s submitted_answer_count=%s",
        attempt.id,
        attempt.user_id,
        section.section_type,
        len(submitted_answers),
    )
    AttemptAnswer.objects.filter(attempt_section=section).delete()
    answers_by_index = {
        int(item["question_index"]): str(item.get("selected_option", ""))
        for item in submitted_answers
    }

    score = 0
    for question_index, question in enumerate(section.question_payload or []):
        correct_answer = str(question.get("correct_answer", {}).get("answer", ""))
        selected_answer = answers_by_index.get(question_index, "")
        is_correct = selected_answer == correct_answer
        if is_correct:
            score += 1
        AttemptAnswer.objects.create(
            attempt_section=section,
            question_index=question_index,
            user_answer={"selected_option": selected_answer},
            is_correct=is_correct,
            penalty_applied=0,
        )

    section.adjusted_score = score
    section.save(update_fields=["adjusted_score"])
    attempt.overall_adjusted_score = score
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["overall_adjusted_score", "status", "completed_at"])
    record_test_progress(attempt.user, section.section_type, score)
    logger.info(
        "Saved section attempt result attempt_id=%s user_id=%s score=%s question_count=%s",
        attempt.id,
        attempt.user_id,
        score,
        len(section.question_payload or []),
    )
    return {
        "attempt_id": attempt.id,
        "overall_score": score,
        "section_score": score,
    }


def record_practice_progress(
    user: User,
    section_type: str,
    solved_increment: int = 1,
    assessment_type: str | None = None,
) -> SectionProgress:
    resolved_assessment_type = assessment_type or get_module_assessment_type(section_type)
    progress, _ = SectionProgress.objects.get_or_create(
        user=user,
        assessment_type=resolved_assessment_type,
        section_type=section_type,
    )
    progress.practice_questions_solved += max(0, solved_increment)
    progress.save(update_fields=["practice_questions_solved", "updated_at"])
    logger.info(
        "Recorded practice progress user_id=%s section=%s solved_total=%s",
        user.id,
        section_type,
        progress.practice_questions_solved,
    )
    return progress


def record_test_progress(user: User, section_type: str, score: float, assessment_type: str | None = None) -> SectionProgress:
    resolved_assessment_type = assessment_type or get_module_assessment_type(section_type)
    progress, _ = SectionProgress.objects.get_or_create(
        user=user,
        assessment_type=resolved_assessment_type,
        section_type=section_type,
    )
    progress.tests_taken += 1
    progress.last_test_score = score
    progress.save(update_fields=["tests_taken", "last_test_score", "updated_at"])
    logger.info(
        "Recorded test progress user_id=%s section=%s tests_taken=%s last_score=%s",
        user.id,
        section_type,
        progress.tests_taken,
        score,
    )
    return progress


def expire_stale_attempts(user: User | None = None) -> int:
    cutoff = timezone.now() - timedelta(seconds=ACTIVE_ATTEMPT_EXPIRY_SECONDS)
    attempts = Attempt.objects.filter(
        status__in=[AttemptStatus.CREATED, AttemptStatus.IN_PROGRESS],
        started_at__lte=cutoff,
    ).prefetch_related("sections")
    if user is not None:
        attempts = attempts.filter(user=user)

    expired_count = 0
    for attempt in attempts:
        complete_attempt_with_zero(attempt, reason="stale_timeout")
        expired_count += 1

    if expired_count:
        logger.info("Auto-completed stale attempts count=%s user_id=%s", expired_count, user.id if user else "all")
    return expired_count


def complete_attempt_with_zero(attempt: Attempt, reason: str = "manual_end") -> Attempt:
    if attempt.status == AttemptStatus.COMPLETED:
        logger.info("Attempt completion skipped attempt_id=%s reason=%s status=completed", attempt.id, reason)
        return attempt

    logger.info(
        "Completing attempt with zero attempt_id=%s user_id=%s mode=%s reason=%s",
        attempt.id,
        attempt.user_id,
        attempt.mode,
        reason,
    )
    for section in attempt.sections.all():
        section.adjusted_score = 0
        if attempt.mode == AttemptMode.FULL_TEST:
            section.question_payload = {}
        section.save(update_fields=["adjusted_score", "question_payload"] if attempt.mode == AttemptMode.FULL_TEST else ["adjusted_score"])

    attempt.overall_adjusted_score = 0
    attempt.status = AttemptStatus.COMPLETED
    attempt.completed_at = timezone.now()
    attempt.save(update_fields=["overall_adjusted_score", "status", "completed_at"])

    if attempt.mode == AttemptMode.FULL_TEST:
        _delete_full_test_session(attempt.id)

    return attempt


def _build_question_batch(attempt_id: int, section_type: str, phase: str, count: int, difficulty: str) -> list[dict[str, Any]]:
    batch = []
    for index in range(count):
        seed = f"{attempt_id}:{section_type}:{phase}:{difficulty}:{index}"
        generated = generate_question(section_type, difficulty, seed)
        batch.append(asdict(generated))
    logger.info(
        "Generated question batch attempt_id=%s section=%s phase=%s difficulty=%s count=%s",
        attempt_id,
        section_type,
        phase,
        difficulty,
        count,
    )
    return batch


def _strip_correct_answer(question: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(question)
    sanitized.pop("correct_answer", None)
    return sanitized


def _serialize_generated_question_for_player(question: dict[str, Any], include_correct_answer: bool) -> dict[str, Any]:
    payload = question.get("payload", {})
    prompt = payload.get("prompt", {})
    options = [str(option) for option in payload.get("options", [])]
    correct_answer = str(question.get("correct_answer", {}).get("answer", ""))
    section_type = question.get("section_type", "")

    preview = {
        "seed": question.get("seed", ""),
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
        "reveal_mode": "context_then_question",
    }

    if include_correct_answer:
        preview["correct_answer"] = correct_answer

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


def _get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info("Initialized Redis client redis_url=%s", settings.REDIS_URL)
    return _redis_client


def _full_test_session_key(attempt_id: int) -> str:
    return f"prepgia:attempt:{attempt_id}:full-test"


def _full_test_session_exists(attempt_id: int) -> bool:
    try:
        exists = bool(_get_redis_client().exists(_full_test_session_key(attempt_id)))
        logger.info("Checked Redis session existence attempt_id=%s exists=%s", attempt_id, exists)
        return exists
    except RedisError as exc:
        raise FullTestSessionError("Redis is unavailable for active full-test sessions.") from exc


def _save_full_test_session(attempt_id: int, payload: dict[str, Any]) -> None:
    try:
        _get_redis_client().setex(
            _full_test_session_key(attempt_id),
            settings.FULL_TEST_REDIS_TTL_SECONDS,
            json.dumps(payload),
        )
        logger.info(
            "Saved full test session to Redis attempt_id=%s ttl_seconds=%s section_count=%s",
            attempt_id,
            settings.FULL_TEST_REDIS_TTL_SECONDS,
            len(payload.get("sections", [])),
        )
    except RedisError as exc:
        raise FullTestSessionError("Could not save the active full-test session to Redis.") from exc


def _load_full_test_session(attempt_id: int) -> dict[str, Any]:
    try:
        client = _get_redis_client()
        key = _full_test_session_key(attempt_id)
        raw = client.get(key)
        if raw:
            client.expire(key, settings.FULL_TEST_REDIS_TTL_SECONDS)
            logger.info(
                "Loaded full test session from Redis attempt_id=%s ttl_refreshed_to=%s",
                attempt_id,
                settings.FULL_TEST_REDIS_TTL_SECONDS,
            )
    except RedisError as exc:
        raise FullTestSessionError("Redis is unavailable for active full-test sessions.") from exc
    if not raw:
        raise FullTestSessionError("This test session expired or could not be found.")
    return json.loads(raw)


def _delete_full_test_session(attempt_id: int) -> None:
    try:
        deleted = _get_redis_client().delete(_full_test_session_key(attempt_id))
        logger.info("Deleted full test session from Redis attempt_id=%s deleted=%s", attempt_id, bool(deleted))
    except RedisError:
        pass
