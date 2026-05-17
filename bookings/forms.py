from django import forms
from django.utils import timezone

from core.forms import BootstrapFormMixin


DATETIME_INPUT_FORMAT = "%Y-%m-%dT%H:%M"


class BookingForm(BootstrapFormMixin, forms.Form):
    title = forms.CharField(label="Тема встречи", max_length=180)
    description = forms.CharField(label="Описание", required=False, widget=forms.Textarea(attrs={"rows": 4}))
    participants_count = forms.IntegerField(label="Количество участников", min_value=1)
    start_at = forms.DateTimeField(
        label="Начало",
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMAT, attrs={"type": "datetime-local"}),
    )
    end_at = forms.DateTimeField(
        label="Окончание",
        input_formats=[DATETIME_INPUT_FORMAT],
        widget=forms.DateTimeInput(format=DATETIME_INPUT_FORMAT, attrs={"type": "datetime-local"}),
    )

    def __init__(self, *args, booking=None, **kwargs):
        initial = kwargs.setdefault("initial", {})
        if booking is not None:
            if booking.start_at:
                initial.setdefault("start_at", timezone.localtime(booking.start_at).strftime(DATETIME_INPUT_FORMAT))
            if booking.end_at:
                initial.setdefault("end_at", timezone.localtime(booking.end_at).strftime(DATETIME_INPUT_FORMAT))
            initial.setdefault("title", booking.title)
            initial.setdefault("description", booking.description)
            initial.setdefault("participants_count", booking.participants_count)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        start_at = cleaned_data.get("start_at")
        end_at = cleaned_data.get("end_at")
        if start_at and end_at and start_at >= end_at:
            raise forms.ValidationError("Время начала должно быть раньше времени окончания.")
        return cleaned_data

