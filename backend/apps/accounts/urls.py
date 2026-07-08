from django.urls import path

from .views import GoogleOAuthConfigView, SessionView


urlpatterns = [
    path("session/", SessionView.as_view(), name="session"),
    path("google/", GoogleOAuthConfigView.as_view(), name="google-config"),
]

