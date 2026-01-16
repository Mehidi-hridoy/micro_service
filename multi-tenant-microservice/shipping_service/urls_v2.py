from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ShipmentViewSetV2, TrackingEventViewSet, 
    ShippingRateViewSet, CalculateRateAPI
)

router = DefaultRouter()
router.register(r'shipments', ShipmentViewSetV2, basename='shipment')
router.register(r'tracking', TrackingEventViewSet, basename='tracking')
router.register(r'rates', ShippingRateViewSet, basename='shipping-rate')

urlpatterns = [
    path('', include(router.urls)),
    path('shipments/bulk/', 
         ShipmentViewSetV2.as_view({'post': 'bulk_create'}), 
         name='shipment-bulk-create'),
    path('shipments/analytics/', 
         ShipmentViewSetV2.as_view({'get': 'analytics'}), 
         name='shipment-analytics'),
    path('calculate-rate/', CalculateRateAPI.as_view(), name='calculate-rate'),
    path('shipments/<int:pk>/add-tracking/', 
         ShipmentViewSetV2.as_view({'post': 'add_tracking_event'}), 
         name='add-tracking'),
    path('shipments/<int:pk>/calculate-rate/', 
         ShipmentViewSetV2.as_view({'get': 'calculate_rate'}), 
         name='shipment-calculate-rate'),
]

