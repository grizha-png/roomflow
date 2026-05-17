from django.urls import path

from .views import BookingCancelView, BookingCreateView, BookingDetailView, BookingListView, BookingUpdateView


app_name = "bookings"


urlpatterns = [
    path("my/", BookingListView.as_view(), name="my_list"),
    path("create/<slug:slug>/", BookingCreateView.as_view(), name="create"),
    path("<int:pk>/", BookingDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", BookingUpdateView.as_view(), name="edit"),
    path("<int:pk>/cancel/", BookingCancelView.as_view(), name="cancel"),
]

