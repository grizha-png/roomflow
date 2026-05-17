from django.contrib import admin

from .models import Equipment, MeetingRoom


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MeetingRoom)
class MeetingRoomAdmin(admin.ModelAdmin):
    list_display = ("name", "location", "floor", "capacity", "approval_policy", "is_active")
    list_filter = ("approval_policy", "is_active", "location")
    search_fields = ("name", "location", "description")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("equipment",)

