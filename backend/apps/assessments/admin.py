from __future__ import annotations

import csv
from datetime import timedelta

from django.contrib import admin, messages
from django.http import HttpResponse
from django.utils import timezone

from backend.apps.tenants.admin_mixins import TenantScopedAdminMixin

from .models import Attempt, AttemptAnswer, AttemptSection, SectionProgress, WordMeaningItem
from .services import (
    clear_attempt_runtime_state,
    expire_stale_attempts,
    finalize_attempt_from_saved_progress,
    recompute_attempt_summary,
    recompute_section_progress_for_user,
)


@admin.register(Attempt)
class AttemptAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "tenant", "user", "assessment_type", "mode", "status", "overall_adjusted_score", "started_at", "completed_at")
    list_filter = ("assessment_type", "mode", "status")
    search_fields = ("user__email",)
    actions = (
        "force_end_selected_attempts",
        "close_selected_stale_attempts",
        "close_all_stale_attempts",
        "recalculate_attempt_summary",
        "clear_selected_runtime_sessions",
        "export_selected_attempts_csv",
    )

    @admin.action(description="Force end selected attempts")
    def force_end_selected_attempts(self, request, queryset):
        updated = 0
        for attempt in queryset.prefetch_related("sections"):
            finalize_attempt_from_saved_progress(attempt, reason="admin_force_end")
            updated += 1
        self.message_user(request, f"Finalized {updated} attempt(s).", level=messages.SUCCESS)

    @admin.action(description="Close selected stale attempts (older than 2 hours)")
    def close_selected_stale_attempts(self, request, queryset):
        cutoff = timezone.now() - timedelta(hours=2)
        updated = 0
        for attempt in queryset.filter(started_at__lte=cutoff).prefetch_related("sections"):
            finalize_attempt_from_saved_progress(attempt, reason="admin_stale_cleanup")
            updated += 1
        self.message_user(request, f"Closed {updated} stale attempt(s).", level=messages.SUCCESS)

    @admin.action(description="Close all stale attempts older than 2 hours")
    def close_all_stale_attempts(self, request, queryset):
        expired = expire_stale_attempts()
        self.message_user(request, f"Closed {expired} stale attempt(s) across all users.", level=messages.SUCCESS)

    @admin.action(description="Recalculate attempt summary")
    def recalculate_attempt_summary(self, request, queryset):
        updated = 0
        for attempt in queryset.prefetch_related("sections__answers"):
            recompute_attempt_summary(attempt)
            updated += 1
        self.message_user(request, f"Recomputed summaries for {updated} attempt(s).", level=messages.SUCCESS)

    @admin.action(description="Clear selected Redis/runtime sessions")
    def clear_selected_runtime_sessions(self, request, queryset):
        updated = 0
        for attempt in queryset:
            clear_attempt_runtime_state(attempt)
            updated += 1
        self.message_user(request, f"Cleared runtime session state for {updated} attempt(s).", level=messages.SUCCESS)

    @admin.action(description="Export selected attempts as CSV")
    def export_selected_attempts_csv(self, request, queryset):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="attempts.csv"'
        writer = csv.writer(response)
        writer.writerow(
            [
                "id",
                "user",
                "assessment_type",
                "mode",
                "status",
                "overall_score",
                "started_at",
                "completed_at",
            ]
        )
        for attempt in queryset.select_related("user"):
            writer.writerow(
                [
                    attempt.id,
                    attempt.user.email,
                    attempt.assessment_type,
                    attempt.mode,
                    attempt.status,
                    attempt.overall_adjusted_score,
                    attempt.started_at.isoformat() if attempt.started_at else "",
                    attempt.completed_at.isoformat() if attempt.completed_at else "",
                ]
            )
        return response


@admin.register(AttemptSection)
class AttemptSectionAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "tenant",
        "attempt",
        "section_type",
        "question_count",
        "adjusted_score",
        "correct_answers_count",
        "incorrect_answers_count",
    )
    list_filter = ("section_type", "attempt__assessment_type")
    search_fields = ("attempt__user__email", "attempt__id")


@admin.register(AttemptAnswer)
class AttemptAnswerAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = ("id", "tenant", "attempt_section", "question_index", "is_correct", "submitted_at")
    list_filter = ("is_correct", "attempt_section__section_type")
    search_fields = ("attempt_section__attempt__user__email", "attempt_section__attempt__id")


@admin.register(SectionProgress)
class SectionProgressAdmin(TenantScopedAdminMixin, admin.ModelAdmin):
    list_display = (
        "tenant",
        "user",
        "assessment_type",
        "section_type",
        "practice_questions_solved",
        "tests_taken",
        "last_test_score",
        "updated_at",
    )
    list_filter = ("assessment_type", "section_type")
    search_fields = ("user__email",)
    actions = ("recompute_selected_dashboard_metrics",)

    @admin.action(description="Recompute selected dashboard metrics")
    def recompute_selected_dashboard_metrics(self, request, queryset):
        seen = set()
        updated = 0
        for progress in queryset.select_related("user"):
            key = (progress.user_id, progress.assessment_type)
            if key in seen:
                continue
            updated += recompute_section_progress_for_user(progress.user, assessment_type=progress.assessment_type)
            seen.add(key)
        self.message_user(request, f"Recomputed {updated} section progress row(s).", level=messages.SUCCESS)


@admin.register(WordMeaningItem)
class WordMeaningItemAdmin(admin.ModelAdmin):
    list_display = ("id", "pair_word_1", "pair_word_2", "odd_word", "relationship_type", "difficulty", "is_active")
    list_filter = ("difficulty", "relationship_type", "is_active")
    search_fields = ("pair_word_1", "pair_word_2", "odd_word")

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
