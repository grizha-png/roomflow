from django.test import TestCase
from django.urls import reverse

from rooms.models import MeetingRoom


class HomePageTests(TestCase):
    def test_home_page_renders(self):
        MeetingRoom.objects.create(
            name="North Star",
            location="HQ",
            floor=2,
            capacity=10,
            description="Комната для командных встреч.",
        )
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RoomFlow")
        self.assertContains(response, "North Star")

