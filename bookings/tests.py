from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from rooms.models import MeetingRoom

from .models import BookingStatus
from .services import create_booking


class BookingServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee", password="password123")
        self.room_auto = MeetingRoom.objects.create(
            name="Aurora",
            location="HQ",
            floor=3,
            capacity=8,
            description="Автоматическая переговорная.",
            approval_policy=MeetingRoom.ApprovalPolicy.AUTOMATIC,
        )
        self.room_manual = MeetingRoom.objects.create(
            name="Vector",
            location="HQ",
            floor=5,
            capacity=12,
            description="Комната с модерацией.",
            approval_policy=MeetingRoom.ApprovalPolicy.MANUAL,
        )
        self.start_at = timezone.now() + timedelta(days=1)
        self.end_at = self.start_at + timedelta(hours=1)

    def test_automatic_room_creates_confirmed_booking(self):
        booking = create_booking(
            room=self.room_auto,
            organizer=self.user,
            title="Daily sync",
            description="Командная встреча.",
            start_at=self.start_at,
            end_at=self.end_at,
            participants_count=6,
        )
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)

    def test_manual_room_creates_pending_booking(self):
        booking = create_booking(
            room=self.room_manual,
            organizer=self.user,
            title="Planning",
            description="Встреча с согласованием.",
            start_at=self.start_at,
            end_at=self.end_at,
            participants_count=7,
        )
        self.assertEqual(booking.status, BookingStatus.PENDING)

    def test_overlap_is_rejected(self):
        create_booking(
            room=self.room_auto,
            organizer=self.user,
            title="Booked slot",
            description="Первое бронирование.",
            start_at=self.start_at,
            end_at=self.end_at,
            participants_count=4,
        )
        with self.assertRaises(ValidationError):
            create_booking(
                room=self.room_auto,
                organizer=self.user,
                title="Conflicting slot",
                description="Второе бронирование.",
                start_at=self.start_at + timedelta(minutes=15),
                end_at=self.end_at + timedelta(minutes=15),
                participants_count=4,
            )


class BookingViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="employee", password="password123")
        self.room = MeetingRoom.objects.create(
            name="Nimbus",
            location="HQ",
            floor=2,
            capacity=10,
            description="Комната для тестов.",
            approval_policy=MeetingRoom.ApprovalPolicy.AUTOMATIC,
        )
        self.booking = create_booking(
            room=self.room,
            organizer=self.user,
            title="Retro",
            description="Ретроспектива.",
            start_at=timezone.now() + timedelta(days=2),
            end_at=timezone.now() + timedelta(days=2, hours=1),
            participants_count=5,
        )

    def test_my_bookings_requires_authentication(self):
        response = self.client.get(reverse("bookings:my_list"))
        self.assertEqual(response.status_code, 302)

    def test_owner_can_cancel_booking(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse("bookings:cancel", args=[self.booking.pk]), follow=True)
        self.booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.status, BookingStatus.CANCELLED)


class ModerationTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(username="employee", password="password123")
        self.moderator = User.objects.create_user(username="moderator", password="password123")
        moderator_group, _ = Group.objects.get_or_create(name="moderator")
        self.moderator.groups.add(moderator_group)
        self.room = MeetingRoom.objects.create(
            name="Helix",
            location="HQ",
            floor=7,
            capacity=10,
            description="Комната с ручным согласованием.",
            approval_policy=MeetingRoom.ApprovalPolicy.MANUAL,
        )
        self.booking = create_booking(
            room=self.room,
            organizer=self.employee,
            title="Board review",
            description="Заседание.",
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, hours=2),
            participants_count=6,
        )

    def test_moderator_can_approve_pending_booking(self):
        self.client.force_login(self.moderator)
        response = self.client.post(
            reverse("dashboard:moderate_booking", args=[self.booking.pk, "approve"]),
            {"comment": "Окно свободно."},
            follow=True,
        )
        self.booking.refresh_from_db()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.booking.status, BookingStatus.CONFIRMED)
        self.assertEqual(self.booking.approved_by, self.moderator)

