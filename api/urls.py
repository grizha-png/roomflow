from django.urls import path

from .views import (
    ApiRootView,
    BookingCancelAPIView,
    BookingDetailAPIView,
    BookingListCreateAPIView,
    BookingModerationAPIView,
    EquipmentListAPIView,
    PendingBookingListAPIView,
    ProfileAPIView,
    RoomDetailAPIView,
    RoomListAPIView,
)


app_name = "api"


urlpatterns = [
    path("", ApiRootView.as_view(), name="root"),
    path("equipment/", EquipmentListAPIView.as_view(), name="equipment-list"),
    path("rooms/", RoomListAPIView.as_view(), name="room-list"),
    path("rooms/<slug:slug>/", RoomDetailAPIView.as_view(), name="room-detail"),
    path("bookings/", BookingListCreateAPIView.as_view(), name="booking-list"),
    path("bookings/pending/", PendingBookingListAPIView.as_view(), name="pending-booking-list"),
    path("bookings/<int:pk>/", BookingDetailAPIView.as_view(), name="booking-detail"),
    path("bookings/<int:pk>/cancel/", BookingCancelAPIView.as_view(), name="booking-cancel"),
    path("bookings/<int:pk>/<str:decision>/", BookingModerationAPIView.as_view(), name="booking-moderation"),
    path("users/me/", ProfileAPIView.as_view(), name="profile"),
]
