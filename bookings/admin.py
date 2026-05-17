from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("title", "room", "organizer", "status", "participants_count", "created_at")
    list_filter = ("status", "room", "created_at")
    search_fields = ("title", "description", "organizer__username", "room__name")
    autocomplete_fields = ("room", "organizer", "approved_by")

