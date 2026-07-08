from __future__ import annotations

from django.conf import settings
from django.db import models


class AttemptMode(models.TextChoices):
    FULL_TEST = "full_test", "Full Test"
    SECTION = "section", "Section"


class AttemptStatus(models.TextChoices):
    CREATED = "created", "Created"
    IN_PROGRESS = "in_progress", "In Progress"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"


class SectionType(models.TextChoices):
    REASONING = "reasoning", "Reasoning"
    PERCEPTUAL_SPEED = "perceptual_speed", "Perceptual Speed"
    NUMBER_SPEED_ACCURACY = "number_speed_accuracy", "Number Speed & Accuracy"
    WORD_MEANING = "word_meaning", "Word Meaning"
    SPATIAL_VISUALIZATION = "spatial_visualization", "Spatial Visualization"


class Attempt(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    mode = models.CharField(max_length=24, choices=AttemptMode.choices)
    status = models.CharField(max_length=24, choices=AttemptStatus.choices, default=AttemptStatus.CREATED)
    overall_adjusted_score = models.FloatField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)


class AttemptSection(models.Model):
    attempt = models.ForeignKey(Attempt, on_delete=models.CASCADE, related_name="sections")
    section_type = models.CharField(max_length=32, choices=SectionType.choices)
    order_index = models.PositiveIntegerField(default=0)
    difficulty = models.CharField(max_length=16, default="easy")
    time_limit_seconds = models.PositiveIntegerField()
    question_count = models.PositiveIntegerField(default=10)
    adjusted_score = models.FloatField(default=0)
    question_payload = models.JSONField(default=dict)


class AttemptAnswer(models.Model):
    attempt_section = models.ForeignKey(AttemptSection, on_delete=models.CASCADE, related_name="answers")
    question_index = models.PositiveIntegerField()
    user_answer = models.JSONField(default=dict, blank=True)
    is_correct = models.BooleanField(blank=True, null=True)
    penalty_applied = models.FloatField(default=0)
    submitted_at = models.DateTimeField(auto_now_add=True)


class SectionProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="section_progress")
    section_type = models.CharField(max_length=32, choices=SectionType.choices)
    practice_questions_solved = models.PositiveIntegerField(default=0)
    tests_taken = models.PositiveIntegerField(default=0)
    last_test_score = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "section_type")
