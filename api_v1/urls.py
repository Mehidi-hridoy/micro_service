from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.UserRegistrationViewV1.as_view(), name='v1-register'),
    path('auth/login/', views.UserLoginViewV1.as_view(), name='v1-login'),
    path('auth/profile/', views.UserProfileViewV1.as_view(), name='v1-profile'),
    
    # Shipment endpoints
    path('shipments/', views.ShipmentListViewV1.as_view(), name='v1-shipment-list'),
    path('shipments/create/', views.ShipmentCreateViewV1.as_view(), name='v1-shipment-create'),
    path('shipments/<str:shipment_id>/', views.ShipmentDetailViewV1.as_view(), name='v1-shipment-detail'),
    path('shipments/<str:shipment_id>/cancel/', views.ShipmentCancelViewV1.as_view(), name='v1-shipment-cancel'),
    
    # Tracking endpoints
    path('tracking/<str:tracking_number>/', views.TrackingViewV1.as_view(), name='v1-track-shipment'),
]