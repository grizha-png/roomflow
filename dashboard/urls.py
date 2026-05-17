from django.urls import path

from .views import ModerateBookingView, ModerationQueueView


app_name = "dashboard"


urlpatterns = [
    path("", ModerationQueueView.as_view(), name="moderation_queue"),
    path("<int:pk>/<str:decision>/", ModerateBookingView.as_view(), name="moderate_booking"),
]

