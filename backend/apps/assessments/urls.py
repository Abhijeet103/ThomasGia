from django.urls import path

from .views import AttemptEndView, AttemptStartView, FullTestQuestionView, FullTestSubmitView, PracticeProgressUpdateView, SectionCatalogView, SectionTestSubmitView


urlpatterns = [
    path("sections/", SectionCatalogView.as_view(), name="sections"),
    path("attempts/start/", AttemptStartView.as_view(), name="attempt-start"),
    path("attempts/<int:attempt_id>/end/", AttemptEndView.as_view(), name="attempt-end"),
    path("practice-progress/", PracticeProgressUpdateView.as_view(), name="practice-progress"),
    path("section-tests/<int:attempt_id>/submit/", SectionTestSubmitView.as_view(), name="section-test-submit"),
    path("full-tests/<int:attempt_id>/question/", FullTestQuestionView.as_view(), name="full-test-question"),
    path("full-tests/<int:attempt_id>/submit/", FullTestSubmitView.as_view(), name="full-test-submit"),
]
