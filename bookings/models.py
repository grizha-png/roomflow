from django.contrib.auth import get_user_model
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import DateTimeRangeField, RangeOperators
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from rooms.models import MeetingRoom


User = get_user_model()


class BookingStatus(models.TextChoices):
    PENDING = "pending", "Ожидает согласования"
    CONFIRMED = "confirmed", "Подтверждено"
    REJECTED = "rejected", "Отклонено"
    CANCELLED = "cancelled", "Отменено"
    COMPLETED = "completed", "Завершено"


class BookingQuerySet(models.QuerySet):
    def active(self):
        return self.filter(status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED])


class Booking(models.Model):
    room = models.ForeignKey(MeetingRoom, on_delete=models.CASCADE, related_name="bookings", verbose_name="Переговорная")
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings", verbose_name="Организатор")
    title = models.CharField("Тема встречи", max_length=180)
    description = models.TextField("Описание", blank=True)
    timeslot = DateTimeRangeField("Интервал бронирования")
    participants_count = models.PositiveIntegerField("Количество участников")
    status = models.CharField(
        "Статус",
        max_length=16,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
    )
    moderation_comment = models.TextField("Комментарий модератора", blank=True)
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderated_bookings",
        verbose_name="Подтвердил",
    )
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    objects = BookingQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        constraints = [
            models.CheckConstraint(
                condition=Q(participants_count__gte=1),
                name="booking_participants_count_gte_1",
            ),
            ExclusionConstraint(
                name="prevent_active_booking_overlap",
                expressions=[
                    (F("timeslot"), RangeOperators.OVERLAPS),
                    (F("room"), RangeOperators.EQUAL),
                ],
                condition=Q(status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED]),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} — {self.room.name}"

    def clean(self):
        errors = {}
        if self.timeslot:
            if self.timeslot.lower and self.timeslot.upper and self.timeslot.lower >= self.timeslot.upper:
                errors["timeslot"] = "Начало бронирования должно быть раньше окончания."
            if self.timeslot.lower and self.timeslot.lower < timezone.now():
                errors["timeslot"] = "Нельзя создать бронирование в прошлом."
        if self.room_id:
            if not self.room.is_active:
                errors["room"] = "Эта переговорная недоступна для бронирования."
            if self.participants_count and self.participants_count > self.room.capacity:
                errors["participants_count"] = "Количество участников превышает вместимость комнаты."
        if errors:
            from django.core.exceptions import ValidationError

            raise ValidationError(errors)

    @property
    def start_at(self):
        return self.timeslot.lower if self.timeslot else None

    @property
    def end_at(self):
        return self.timeslot.upper if self.timeslot else None

    @property
    def status_badge_class(self) -> str:
        return f"status-{self.status}"

    def get_absolute_url(self):
        return reverse("bookings:detail", kwargs={"pk": self.pk})

    def can_edit(self, user) -> bool:
        if not user.is_authenticated:
            return False
        return (user == self.organizer or user.is_staff) and self.status not in {
            BookingStatus.CANCELLED,
            BookingStatus.COMPLETED,
            BookingStatus.REJECTED,
        }

    def can_cancel(self, user) -> bool:
        if not user.is_authenticated:
            return False
        return (user == self.organizer or user.is_staff) and self.status not in {
            BookingStatus.CANCELLED,
            BookingStatus.COMPLETED,
        }

