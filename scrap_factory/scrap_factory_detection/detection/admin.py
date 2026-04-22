from django.contrib import admin
from .models import SafetyEvent


@admin.register(SafetyEvent)
class SafetyEventAdmin(admin.ModelAdmin):
    list_display  = ("id", "belt_status", "area_type", "timestamp")
    list_filter   = ("belt_status", "area_type")
    readonly_fields = ("timestamp",)
    ordering = ("-timestamp",)