from django.urls import path
from . import views_tracking

urlpatterns = [
    path('<str:tracking_number>/', views_tracking.TrackingViewV2.as_view(), name='v2-track-shipment'),
]