from .views import (
    BookingViewSet,
    BookingIdViewSet,
    BookingIdCollaboratorsViewSet,
    BookingIdInstanceIdPowerViewSet,
    BookingIdInstanceIdReprovisionViewSet,
    BookingIdExtend,
    BookingIdStatusViewSet,
)
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns

app_name = "booking_api"
urlpatterns = format_suffix_patterns(
    [
        path("booking/", BookingViewSet.as_view({"get": "list", "post": "create"})),
        path("booking/<int:booking_id>/", BookingIdViewSet.as_view({"get": "get_booking", "delete": "destroy"})),
        path("booking/<int:booking_id>/status/", BookingIdStatusViewSet.as_view({"get": "get_status"})),
        path("booking/<int:booking_id>/collaborators/", 
            BookingIdCollaboratorsViewSet.as_view({"get": "get_collaborators", "post": "post"})
            ),
        path("booking/<int:booking_id>/instance/<str:instance_id>/power/",
            BookingIdInstanceIdPowerViewSet.as_view({"post": "power"})
            ),
        path("booking/<int:booking_id>/extend/", BookingIdExtend.as_view({"post": "extend"})),
        path("booking/<int:booking_id>/instance/<str:instance_id>/reprovision/",
            BookingIdInstanceIdReprovisionViewSet.as_view({"post": "reprovision"})
            ),
    ]
)
