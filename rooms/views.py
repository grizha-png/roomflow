from django.db.models import Q
from django.views.generic import DetailView, ListView

from bookings.models import Booking, BookingStatus

from .forms import RoomFilterForm
from .models import MeetingRoom


class RoomListView(ListView):
    template_name = "rooms/room_list.html"
    model = MeetingRoom
    context_object_name = "rooms"
    paginate_by = 12

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = RoomFilterForm(self.request.GET or None)
        return self._filter_form

    def get_queryset(self):
        queryset = MeetingRoom.objects.filter(is_active=True).prefetch_related("equipment")
        form = self.get_filter_form()
        if form.is_valid():
            q = form.cleaned_data.get("q")
            location = form.cleaned_data.get("location")
            min_capacity = form.cleaned_data.get("min_capacity")
            approval_policy = form.cleaned_data.get("approval_policy")
            equipment = form.cleaned_data.get("equipment")
            if q:
                queryset = queryset.filter(
                    Q(name__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q)
                )
            if location:
                queryset = queryset.filter(location__icontains=location)
            if min_capacity:
                queryset = queryset.filter(capacity__gte=min_capacity)
            if approval_policy:
                queryset = queryset.filter(approval_policy=approval_policy)
            if equipment:
                queryset = queryset.filter(equipment__in=equipment).distinct()
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        return context


class RoomDetailView(DetailView):
    template_name = "rooms/room_detail.html"
    model = MeetingRoom
    context_object_name = "room"
    slug_field = "slug"
    slug_url_kwarg = "slug"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["upcoming_bookings"] = (
            Booking.objects.filter(
                room=self.object,
                status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED],
            )
            .select_related("organizer")
            .order_by("timeslot")[:8]
        )
        return context

