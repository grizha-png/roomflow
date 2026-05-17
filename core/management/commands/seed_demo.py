from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from rooms.models import Equipment, MeetingRoom


class Command(BaseCommand):
    help = "Create demo rooms, equipment and users for RoomFlow."

    def handle(self, *args, **options):
        moderator_group, _ = Group.objects.get_or_create(name="moderator")

        equipment_items = [
            ("Проектор", "projector"),
            ("Видеоконференц-связь", "video-conference"),
            ("Маркерная доска", "whiteboard"),
            ("Телевизор 4K", "tv-4k"),
        ]
        equipment_objects = []
        for name, slug in equipment_items:
            item, _ = Equipment.objects.get_or_create(name=name, slug=slug)
            equipment_objects.append(item)

        room_specs = [
            {
                "name": "Aurora",
                "slug": "aurora",
                "location": "Главный офис",
                "floor": 3,
                "capacity": 8,
                "approval_policy": MeetingRoom.ApprovalPolicy.AUTOMATIC,
                "equipment": equipment_objects[:3],
            },
            {
                "name": "Vector",
                "slug": "vector",
                "location": "Главный офис",
                "floor": 5,
                "capacity": 12,
                "approval_policy": MeetingRoom.ApprovalPolicy.MANUAL,
                "equipment": equipment_objects[1:],
            },
        ]

        for spec in room_specs:
            equipment = spec.pop("equipment")
            room, _ = MeetingRoom.objects.get_or_create(
                slug=spec["slug"],
                defaults={
                    **spec,
                    "description": "Демо-переговорная для первичной проверки интерфейса и сценариев бронирования.",
                },
            )
            room.equipment.set(equipment)

        if not User.objects.filter(username="employee").exists():
            User.objects.create_user(
                username="employee",
                password="employee",
                first_name="Demo",
                last_name="Employee",
                email="employee@example.com",
            )

        if not User.objects.filter(username="moderator").exists():
            moderator = User.objects.create_user(
                username="moderator",
                password="moderator",
                first_name="Demo",
                last_name="Moderator",
                email="moderator@example.com",
                is_staff=True,
            )
            moderator.groups.add(moderator_group)

        self.stdout.write(self.style.SUCCESS("Demo data created or updated successfully."))

