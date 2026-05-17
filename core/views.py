from django.views.generic import TemplateView

from rooms.models import MeetingRoom


class HomeView(TemplateView):
    template_name = "core/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["featured_rooms"] = MeetingRoom.objects.filter(is_active=True).prefetch_related("equipment")[:3]
        if self.request.user.is_authenticated:
            context["recent_bookings"] = self.request.user.bookings.select_related("room").order_by("-created_at")[:5]
        else:
            context["recent_bookings"] = []
        return context

