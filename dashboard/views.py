from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView

from bookings.models import Booking, BookingStatus
from bookings.services import moderate_booking
from core.mixins import ModeratorRequiredMixin


class ModerationQueueView(ModeratorRequiredMixin, ListView):
    template_name = "dashboard/moderation_queue.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return (
            Booking.objects.filter(status=BookingStatus.PENDING)
            .select_related("room", "organizer")
            .order_by("created_at")
        )


class ModerateBookingView(ModeratorRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking, pk=kwargs["pk"])
        decision = kwargs["decision"]
        try:
            moderate_booking(
                booking=booking,
                moderator=request.user,
                approve=decision == "approve",
                comment=request.POST.get("comment", "").strip(),
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("dashboard:moderation_queue")
        if decision == "approve":
            messages.success(request, "Заявка подтверждена.")
        else:
            messages.success(request, "Заявка отклонена.")
        return redirect("dashboard:moderation_queue")

