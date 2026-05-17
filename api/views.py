from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import generics, permissions, response, serializers, status, views
from rest_framework.reverse import reverse

from bookings.models import Booking, BookingStatus
from bookings.services import cancel_booking, create_booking, moderate_booking, update_booking
from rooms.models import Equipment, MeetingRoom

from .serializers import (
    BookingCreateSerializer,
    BookingSerializer,
    BookingUpdateSerializer,
    EquipmentSerializer,
    MeetingRoomDetailSerializer,
    MeetingRoomListSerializer,
    ModerationSerializer,
    UserSummarySerializer,
)


def handle_domain_error(exc):
    if isinstance(exc, ValidationError):
        detail = exc.message_dict if hasattr(exc, "message_dict") else {"detail": exc.messages}
        return response.Response(detail, status=status.HTTP_400_BAD_REQUEST)
    if isinstance(exc, PermissionDenied):
        return response.Response({"detail": str(exc)}, status=status.HTTP_403_FORBIDDEN)
    raise exc


class ModeratorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.groups.filter(name="moderator").exists()))


class BookingAccessPermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user == obj.organizer or user.is_staff or user.groups.filter(name="moderator").exists())
        )


class ApiRootView(views.APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        operation_id="api_root",
        responses={
            200: inline_serializer(
                name="ApiRootResponse",
                fields={
                    "rooms": serializers.URLField(),
                    "equipment": serializers.URLField(),
                    "bookings": serializers.URLField(),
                    "pending_bookings": serializers.URLField(),
                    "profile": serializers.URLField(),
                    "schema": serializers.URLField(),
                    "swagger": serializers.URLField(),
                },
            ),
            401: OpenApiResponse(description="Для части ресурсов требуется аутентификация."),
        },
    )
    def get(self, request, *args, **kwargs):
        return response.Response(
            {
                "rooms": reverse("api:room-list", request=request),
                "equipment": reverse("api:equipment-list", request=request),
                "bookings": reverse("api:booking-list", request=request),
                "pending_bookings": reverse("api:pending-booking-list", request=request),
                "profile": reverse("api:profile", request=request),
                "schema": reverse("api-schema", request=request),
                "swagger": reverse("api-swagger-ui", request=request),
            }
        )


class EquipmentListAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = EquipmentSerializer
    queryset = Equipment.objects.order_by("name")


class RoomListAPIView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MeetingRoomListSerializer

    def get_queryset(self):
        queryset = MeetingRoom.objects.filter(is_active=True).prefetch_related("equipment").order_by("name")
        params = self.request.query_params
        q = params.get("q", "").strip()
        location = params.get("location", "").strip()
        min_capacity = params.get("min_capacity", "").strip()
        approval_policy = params.get("approval_policy", "").strip()
        equipment_ids = [value for value in params.getlist("equipment") if value]
        if q:
            queryset = queryset.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(location__icontains=q))
        if location:
            queryset = queryset.filter(location__icontains=location)
        if min_capacity:
            queryset = queryset.filter(capacity__gte=min_capacity)
        if approval_policy:
            queryset = queryset.filter(approval_policy=approval_policy)
        if equipment_ids:
            queryset = queryset.filter(equipment__in=equipment_ids).distinct()
        return queryset


class RoomDetailAPIView(generics.RetrieveAPIView):
    permission_classes = [permissions.AllowAny]
    serializer_class = MeetingRoomDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return MeetingRoom.objects.filter(is_active=True).prefetch_related("equipment")

    def get_object(self):
        room = super().get_object()
        room.api_upcoming_bookings = (
            room.bookings.filter(status__in=[BookingStatus.PENDING, BookingStatus.CONFIRMED])
            .select_related("organizer")
            .order_by("timeslot")[:8]
        )
        return room


class BookingListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return (
            Booking.objects.filter(organizer=self.request.user)
            .select_related("room", "organizer", "approved_by")
            .order_by("-created_at")
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return BookingCreateSerializer
        return BookingSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        room = generics.get_object_or_404(MeetingRoom.objects.filter(is_active=True), slug=serializer.validated_data["room_slug"])
        try:
            booking = create_booking(
                room=room,
                organizer=request.user,
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                start_at=serializer.validated_data["start_at"],
                end_at=serializer.validated_data["end_at"],
                participants_count=serializer.validated_data["participants_count"],
            )
        except Exception as exc:
            return handle_domain_error(exc)
        return response.Response(
            BookingSerializer(booking, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )


class BookingDetailAPIView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated, BookingAccessPermission]

    def get_queryset(self):
        return Booking.objects.select_related("room", "organizer", "approved_by")

    def get_serializer_class(self):
        if self.request.method in {"PUT", "PATCH"}:
            return BookingUpdateSerializer
        return BookingSerializer

    def get_serializer_context(self):
        return {"request": self.request}

    def get_object(self):
        obj = super().get_object()
        self.check_object_permissions(self.request, obj)
        return obj

    def update(self, request, *args, **kwargs):
        booking = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            booking = update_booking(
                booking=booking,
                actor=request.user,
                title=serializer.validated_data["title"],
                description=serializer.validated_data.get("description", ""),
                start_at=serializer.validated_data["start_at"],
                end_at=serializer.validated_data["end_at"],
                participants_count=serializer.validated_data["participants_count"],
            )
        except Exception as exc:
            return handle_domain_error(exc)
        return response.Response(BookingSerializer(booking, context=self.get_serializer_context()).data)


class BookingCancelAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: BookingSerializer})
    def post(self, request, pk, *args, **kwargs):
        booking = generics.get_object_or_404(Booking.objects.select_related("room", "organizer", "approved_by"), pk=pk)
        try:
            booking = cancel_booking(booking=booking, actor=request.user)
        except Exception as exc:
            return handle_domain_error(exc)
        return response.Response(BookingSerializer(booking, context={"request": request}).data)


class PendingBookingListAPIView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, ModeratorPermission]
    serializer_class = BookingSerializer

    def get_queryset(self):
        return (
            Booking.objects.filter(status=BookingStatus.PENDING)
            .select_related("room", "organizer", "approved_by")
            .order_by("created_at")
        )

    def get_serializer_context(self):
        return {"request": self.request}


class BookingModerationAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated, ModeratorPermission]

    @extend_schema(request=ModerationSerializer, responses={200: BookingSerializer})
    def post(self, request, pk, decision, *args, **kwargs):
        serializer = ModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = generics.get_object_or_404(Booking.objects.select_related("room", "organizer", "approved_by"), pk=pk)
        try:
            booking = moderate_booking(
                booking=booking,
                moderator=request.user,
                approve=decision == "approve",
                comment=serializer.validated_data.get("comment", ""),
            )
        except Exception as exc:
            return handle_domain_error(exc)
        return response.Response(BookingSerializer(booking, context={"request": request}).data)


class ProfileAPIView(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(request=None, responses={200: UserSummarySerializer})
    def get(self, request, *args, **kwargs):
        return response.Response(UserSummarySerializer(request.user).data)
