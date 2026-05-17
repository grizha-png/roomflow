from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from bookings.models import BookingStatus
from bookings.services import create_booking
from rooms.models import Equipment, MeetingRoom


class ApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="employee", password="password123")
        self.moderator = User.objects.create_user(username="moderator", password="password123", is_staff=True)
        moderator_group, _ = Group.objects.get_or_create(name="moderator")
        self.moderator.groups.add(moderator_group)

        self.equipment = Equipment.objects.create(name="Проектор")
        self.room_auto = MeetingRoom.objects.create(
            name="Atlas",
            location="HQ",
            floor=6,
            capacity=12,
            description="Переговорная для презентаций.",
            approval_policy=MeetingRoom.ApprovalPolicy.AUTOMATIC,
        )
        self.room_auto.equipment.add(self.equipment)

        self.room_manual = MeetingRoom.objects.create(
            name="Vector",
            location="HQ",
            floor=5,
            capacity=10,
            description="Переговорная с ручным согласованием.",
            approval_policy=MeetingRoom.ApprovalPolicy.MANUAL,
        )

        self.booking = create_booking(
            room=self.room_auto,
            organizer=self.user,
            title="API sync",
            description="Проверка API.",
            start_at=timezone.now() + timedelta(days=1),
            end_at=timezone.now() + timedelta(days=1, hours=1),
            participants_count=5,
        )

    def test_api_root_is_available(self):
        response = self.client.get(reverse("api:root"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("rooms", response.json())
        self.assertIn("swagger", response.json())

    def test_room_list_returns_rooms(self):
        response = self.client.get(reverse("api:room-list"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["slug"], self.room_auto.slug)

    def test_room_detail_returns_equipment_and_upcoming_bookings(self):
        response = self.client.get(reverse("api:room-detail", args=[self.room_auto.slug]))
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["equipment"][0]["name"], "Проектор")
        self.assertEqual(payload["upcoming_bookings"][0]["title"], "API sync")

    def test_booking_list_requires_authentication(self):
        response = self.client.get(reverse("api:booking-list"))
        self.assertEqual(response.status_code, 403)

    def test_booking_create_and_list_work(self):
        self.client.force_authenticate(self.user)
        create_response = self.client.post(
            reverse("api:booking-list"),
            {
                "room_slug": self.room_manual.slug,
                "title": "Planning",
                "description": "Новая заявка.",
                "participants_count": 4,
                "start_at": (timezone.now() + timedelta(days=2)).isoformat(),
                "end_at": (timezone.now() + timedelta(days=2, hours=1)).isoformat(),
            },
            format="json",
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["status"], BookingStatus.PENDING)

        list_response = self.client.get(reverse("api:booking-list"))
        self.assertEqual(list_response.status_code, 200)
        self.assertGreaterEqual(len(list_response.json()), 2)

    def test_booking_update_and_cancel_work(self):
        self.client.force_authenticate(self.user)
        update_response = self.client.patch(
            reverse("api:booking-detail", args=[self.booking.pk]),
            {
                "title": "Updated title",
                "description": "Обновленное описание.",
                "participants_count": 6,
                "start_at": self.booking.start_at.isoformat(),
                "end_at": self.booking.end_at.isoformat(),
            },
            format="json",
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["title"], "Updated title")

        cancel_response = self.client.post(reverse("api:booking-cancel", args=[self.booking.pk]), format="json")
        self.assertEqual(cancel_response.status_code, 200)
        self.assertEqual(cancel_response.json()["status"], BookingStatus.CANCELLED)

    def test_pending_queue_and_moderation_work(self):
        pending_booking = create_booking(
            room=self.room_manual,
            organizer=self.user,
            title="Manual booking",
            description="Ждет модерации.",
            start_at=timezone.now() + timedelta(days=3),
            end_at=timezone.now() + timedelta(days=3, hours=1),
            participants_count=4,
        )
        self.client.force_authenticate(self.moderator)

        queue_response = self.client.get(reverse("api:pending-booking-list"))
        self.assertEqual(queue_response.status_code, 200)
        self.assertEqual(queue_response.json()[0]["title"], "Manual booking")

        moderation_response = self.client.post(
            reverse("api:booking-moderation", args=[pending_booking.pk, "approve"]),
            {"comment": "Окно свободно."},
            format="json",
        )
        self.assertEqual(moderation_response.status_code, 200)
        self.assertEqual(moderation_response.json()["status"], BookingStatus.CONFIRMED)

    def test_openapi_schema_and_swagger_are_available(self):
        schema_response = self.client.get(reverse("api-schema"))
        swagger_response = self.client.get(reverse("api-swagger-ui"))
        self.assertEqual(schema_response.status_code, 200)
        self.assertEqual(swagger_response.status_code, 200)
        self.assertContains(schema_response, "openapi")
