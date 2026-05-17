from django.test import TestCase
from django.urls import reverse

from .models import Equipment, MeetingRoom


class RoomViewsTests(TestCase):
    def setUp(self):
        self.projector = Equipment.objects.create(name="Проектор")
        self.room = MeetingRoom.objects.create(
            name="Axiom",
            location="HQ",
            floor=4,
            capacity=14,
            description="Большая переговорная.",
            approval_policy=MeetingRoom.ApprovalPolicy.AUTOMATIC,
        )
        self.room.equipment.add(self.projector)

    def test_room_list_displays_room(self):
        response = self.client.get(reverse("rooms:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Axiom")

    def test_room_detail_displays_equipment(self):
        response = self.client.get(reverse("rooms:detail", args=[self.room.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Проектор")

