from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ShipmentViewSetV1, TrackingEventViewSet

router = DefaultRouter()
router.register(r'shipments', ShipmentViewSetV1, basename='shipment')
router.register(r'tracking', TrackingEventViewSet, basename='tracking')

urlpatterns = [
    path('', include(router.urls)),
    path('shipments/<int:pk>/update-status/', 
         ShipmentViewSetV1.as_view({'post': 'update_status'}), 
         name='update-status'),
]

