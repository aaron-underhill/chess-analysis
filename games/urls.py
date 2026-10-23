from django.urls import path

from . import views

app_name = "games"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("refresh/", views.refresh, name="refresh"),
    path("api/stats/", views.api_stats, name="api_stats"),
    path("cron/import/", views.cron_import, name="cron_import"),
]
