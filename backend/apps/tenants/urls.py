from django.urls import path

from .views import TenantAccessActivationView


app_name = "tenants"

urlpatterns = [
    path("activate/", TenantAccessActivationView.as_view(), name="activate"),
]
