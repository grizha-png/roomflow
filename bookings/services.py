from __future__ import annotations

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.backends.postgresql.psycopg_any import DateTimeTZRange
from django.utils import timezone

from rooms.models import MeetingRoom

from .models import Booking, BookingStatus


ACTIVE_STATUSES = [BookingStatus.PENDING, BookingStatus.CONFIRMED]


def normalize_datetime(value):
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def build_timeslot(start_at, end_at):
    return DateTimeTZRange(normalize_datetime(start_at), normalize_datetime(end_at), "[)")


def validate_booking_payload(
    *,
    room: MeetingRoom,
    start_at,
    end_at,
    participants_count: int,
    exclude_booking: Booking | None = None,
):
    errors = {}
    start_at = normalize_datetime(start_at)
    end_at = normalize_datetime(end_at)
    if not room.is_active:
        errors["room"] = "Переговорная недоступна для бронирования."
    if start_at >= end_at:
        errors["end_at"] = "Время окончания должно быть позже времени начала."
    if start_at < timezone.now():
        errors["start_at"] = "Нельзя создать бронирование в прошлом."
    if participants_count > room.capacity:
        errors["participants_count"] = "Количество участников превышает вместимость комнаты."
    if errors:
        raise ValidationError(errors)

    timeslot = build_timeslot(start_at, end_at)
    overlap_qs = Booking.objects.active().filter(room=room, timeslot__overlap=timeslot)
    if exclude_booking is not None:
        overlap_qs = overlap_qs.exclude(pk=exclude_booking.pk)
    if overlap_qs.exists():
        raise ValidationError({"__all__": "Выбранный интервал уже пересекается с другим активным бронированием."})
    return timeslot


def create_booking(*, room: MeetingRoom, organizer, title: str, description: str, start_at, end_at, participants_count: int):
    timeslot = validate_booking_payload(
        room=room,
        start_at=start_at,
        end_at=end_at,
        participants_count=participants_count,
    )
    status = BookingStatus.CONFIRMED if room.approval_policy == room.ApprovalPolicy.AUTOMATIC else BookingStatus.PENDING
    booking = Booking(
        room=room,
        organizer=organizer,
        title=title,
        description=description,
        participants_count=participants_count,
        timeslot=timeslot,
        status=status,
    )
    try:
        with transaction.atomic():
            booking.full_clean()
            booking.save()
    except IntegrityError as exc:
        raise ValidationError({"__all__": "Не удалось сохранить бронирование из-за конфликта по времени."}) from exc
    return booking


def update_booking(*, booking: Booking, actor, title: str, description: str, start_at, end_at, participants_count: int):
    if not booking.can_edit(actor):
        raise PermissionDenied("Недостаточно прав для редактирования этого бронирования.")
    timeslot = validate_booking_payload(
        room=booking.room,
        start_at=start_at,
        end_at=end_at,
        participants_count=participants_count,
        exclude_booking=booking,
    )
    booking.title = title
    booking.description = description
    booking.participants_count = participants_count
    booking.timeslot = timeslot
    if booking.room.approval_policy == booking.room.ApprovalPolicy.MANUAL:
        booking.status = BookingStatus.PENDING
        booking.approved_by = None
        booking.moderation_comment = ""
    try:
        with transaction.atomic():
            booking.full_clean()
            booking.save()
    except IntegrityError as exc:
        raise ValidationError({"__all__": "Изменения не сохранены: выбранный интервал конфликтует с другим бронированием."}) from exc
    return booking


def cancel_booking(*, booking: Booking, actor):
    if not booking.can_cancel(actor):
        raise PermissionDenied("Недостаточно прав для отмены этого бронирования.")
    booking.status = BookingStatus.CANCELLED
    booking.save(update_fields=["status", "updated_at"])
    return booking


def moderate_booking(*, booking: Booking, moderator, approve: bool, comment: str = ""):
    if not moderator.is_authenticated or not (moderator.is_staff or moderator.groups.filter(name="moderator").exists()):
        raise PermissionDenied("Недостаточно прав для согласования.")
    if booking.status != BookingStatus.PENDING:
        raise ValidationError({"__all__": "Согласовывать можно только заявки в статусе ожидания."})
    booking.status = BookingStatus.CONFIRMED if approve else BookingStatus.REJECTED
    booking.approved_by = moderator
    booking.moderation_comment = comment
    booking.save(update_fields=["status", "approved_by", "moderation_comment", "updated_at"])
    return booking

