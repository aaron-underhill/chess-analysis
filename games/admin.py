from django.contrib import admin

from .models import Game, ImportRun


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ("played_at", "opponent", "color", "result", "speed", "opening_name", "analyzed")
    list_filter = ("platform", "result", "color", "speed", "analyzed")
    search_fields = ("opponent", "opening_name", "eco")
    date_hierarchy = "played_at"


@admin.register(ImportRun)
class ImportRunAdmin(admin.ModelAdmin):
    list_display = ("finished_at", "source", "months_checked", "new_games")
    list_filter = ("source",)
