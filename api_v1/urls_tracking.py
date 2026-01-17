from django.urls import path
from . import views_tracking

urlpatterns = [
    path('<str:tracking_number>/', views_tracking.TrackingViewV1.as_view(), name='v1-track-shipment'),
]