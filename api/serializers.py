from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from bookings.models import Booking
from rooms.models import Equipment, MeetingRoom


User = get_user_model()


class EquipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Equipment
        fields = ("id", "name", "slug", "description")


class BookingSummarySerializer(serializers.ModelSerializer):
    organizer = serializers.SerializerMethodField()
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Booking
        fields = ("id", "title", "organizer", "start_at", "end_at", "status", "status_display")

    def get_organizer(self, obj):
        return obj.organizer.get_full_name() or obj.organizer.username


class MeetingRoomListSerializer(serializers.ModelSerializer):
    equipment = EquipmentSerializer(many=True, read_only=True)
    requires_moderation = serializers.BooleanField(read_only=True)

    class Meta:
        model = MeetingRoom
        fields = (
            "id",
            "name",
            "slug",
            "location",
            "floor",
            "capacity",
            "description",
            "approval_policy",
            "is_active",
            "requires_moderation",
            "equipment",
        )


class MeetingRoomDetailSerializer(MeetingRoomListSerializer):
    upcoming_bookings = serializers.SerializerMethodField()

    class Meta(MeetingRoomListSerializer.Meta):
        fields = MeetingRoomListSerializer.Meta.fields + (
            "created_at",
            "updated_at",
            "upcoming_bookings",
        )

    @extend_schema_field(BookingSummarySerializer(many=True))
    def get_upcoming_bookings(self, obj):
        bookings = getattr(obj, "api_upcoming_bookings", [])
        return BookingSummarySerializer(bookings, many=True).data


class BookingSerializer(serializers.ModelSerializer):
    room = serializers.SerializerMethodField()
    organizer = serializers.SerializerMethodField()
    approved_by = serializers.SerializerMethodField()
    start_at = serializers.DateTimeField(read_only=True)
    end_at = serializers.DateTimeField(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    status_badge_class = serializers.CharField(read_only=True)
    can_edit = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (
            "id",
            "title",
            "description",
            "participants_count",
            "status",
            "status_display",
            "status_badge_class",
            "moderation_comment",
            "room",
            "organizer",
            "approved_by",
            "start_at",
            "end_at",
            "created_at",
            "updated_at",
            "can_edit",
            "can_cancel",
        )

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "id": {"type": "integer"},
                "name": {"type": "string"},
                "slug": {"type": "string"},
                "location": {"type": "string"},
                "floor": {"type": "integer"},
            },
        }
    )
    def get_room(self, obj):
        return {
            "id": obj.room_id,
            "name": obj.room.name,
            "slug": obj.room.slug,
            "location": obj.room.location,
            "floor": obj.room.floor,
        }

    @extend_schema_field(
        {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "full_name": {"type": "string"},
            },
        }
    )
    def get_organizer(self, obj):
        return {
            "username": obj.organizer.username,
            "full_name": obj.organizer.get_full_name(),
        }

    @extend_schema_field(
        {
            "type": "object",
            "nullable": True,
            "properties": {
                "username": {"type": "string"},
                "full_name": {"type": "string"},
            },
        }
    )
    def get_approved_by(self, obj):
        if not obj.approved_by:
            return None
        return {
            "username": obj.approved_by.username,
            "full_name": obj.approved_by.get_full_name(),
        }

    @extend_schema_field({"type": "boolean"})
    def get_can_edit(self, obj):
        user = getattr(self.context.get("request"), "user", None)
        return bool(user and obj.can_edit(user))

    @extend_schema_field({"type": "boolean"})
    def get_can_cancel(self, obj):
        user = getattr(self.context.get("request"), "user", None)
        return bool(user and obj.can_cancel(user))


class BookingCreateSerializer(serializers.Serializer):
    room_slug = serializers.SlugField()
    title = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    participants_count = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class BookingUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=180)
    description = serializers.CharField(required=False, allow_blank=True)
    participants_count = serializers.IntegerField(min_value=1)
    start_at = serializers.DateTimeField()
    end_at = serializers.DateTimeField()


class ModerationSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True)


class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "email", "full_name", "is_staff", "roles")

    def get_full_name(self, obj):
        return obj.get_full_name()

    def get_roles(self, obj):
        roles = ["employee"]
        if obj.groups.filter(name="moderator").exists():
            roles.append("moderator")
        if obj.is_staff:
            roles.append("admin")
        return roles
