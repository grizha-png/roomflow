from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from rooms.models import MeetingRoom

from .forms import BookingForm
from .models import Booking, BookingStatus
from .services import cancel_booking, create_booking, update_booking


def attach_validation_errors(form, error: ValidationError):
    if hasattr(error, "message_dict"):
        for field, messages_list in error.message_dict.items():
            target_field = None if field == "__all__" else field
            for message in messages_list:
                form.add_error(target_field, message)
    else:
        for message in error.messages:
            form.add_error(None, message)


class BookingListView(LoginRequiredMixin, ListView):
    template_name = "bookings/booking_list.html"
    context_object_name = "bookings"

    def get_queryset(self):
        return self.request.user.bookings.select_related("room", "approved_by").order_by("-created_at")


class BookingCreateView(LoginRequiredMixin, FormView):
    template_name = "bookings/booking_form.html"
    form_class = BookingForm

    def dispatch(self, request, *args, **kwargs):
        self.room = get_object_or_404(MeetingRoom, slug=kwargs["slug"], is_active=True)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["room"] = self.room
        context["page_title"] = "Новое бронирование"
        context["submit_label"] = "Создать бронирование"
        return context

    def form_valid(self, form):
        try:
            booking = create_booking(
                room=self.room,
                organizer=self.request.user,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                participants_count=form.cleaned_data["participants_count"],
            )
        except ValidationError as exc:
            attach_validation_errors(form, exc)
            return self.form_invalid(form)
        if booking.status == BookingStatus.PENDING:
            messages.success(self.request, "Заявка создана и отправлена на согласование.")
        else:
            messages.success(self.request, "Бронирование успешно подтверждено.")
        return redirect(booking.get_absolute_url())


class BookingDetailView(LoginRequiredMixin, DetailView):
    template_name = "bookings/booking_detail.html"
    model = Booking
    context_object_name = "booking"

    def get_object(self, queryset=None):
        booking = super().get_object(queryset=queryset)
        user = self.request.user
        allowed = user == booking.organizer or user.is_staff or user.groups.filter(name="moderator").exists()
        if not allowed:
            raise Http404
        return booking


class BookingUpdateView(LoginRequiredMixin, FormView):
    template_name = "bookings/booking_form.html"
    form_class = BookingForm

    def dispatch(self, request, *args, **kwargs):
        self.booking = get_object_or_404(Booking.objects.select_related("room", "organizer"), pk=kwargs["pk"])
        if not self.booking.can_edit(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["booking"] = self.booking
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["room"] = self.booking.room
        context["page_title"] = "Редактирование бронирования"
        context["submit_label"] = "Сохранить изменения"
        context["booking"] = self.booking
        return context

    def form_valid(self, form):
        try:
            booking = update_booking(
                booking=self.booking,
                actor=self.request.user,
                title=form.cleaned_data["title"],
                description=form.cleaned_data["description"],
                start_at=form.cleaned_data["start_at"],
                end_at=form.cleaned_data["end_at"],
                participants_count=form.cleaned_data["participants_count"],
            )
        except ValidationError as exc:
            attach_validation_errors(form, exc)
            return self.form_invalid(form)
        messages.success(self.request, "Бронирование обновлено.")
        return redirect(booking.get_absolute_url())


class BookingCancelView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        booking = get_object_or_404(Booking.objects.select_related("organizer"), pk=kwargs["pk"])
        cancel_booking(booking=booking, actor=request.user)
        messages.success(request, "Бронирование отменено.")
        return HttpResponseRedirect(reverse("bookings:detail", args=[booking.pk]))
