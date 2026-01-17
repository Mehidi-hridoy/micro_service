from django.urls import path
from . import views_shipments

urlpatterns = [
    path('', views_shipments.ShipmentListViewV2.as_view(), name='v2-shipment-list'),
    path('create/', views_shipments.ShipmentCreateViewV2.as_view(), name='v2-shipment-create'),
    path('<str:shipment_id>/', views_shipments.ShipmentDetailViewV2.as_view(), name='v2-shipment-detail'),
    path('<str:shipment_id>/update/', views_shipments.ShipmentUpdateViewV2.as_view(), name='v2-shipment-update'),
    path('<str:shipment_id>/cancel/', views_shipments.ShipmentCancelViewV2.as_view(), name='v2-shipment-cancel'),
    path('<str:shipment_id>/events/', views_shipments.TrackingEventListViewV2.as_view(), name='v2-tracking-events'),
    path('<str:shipment_id>/events/add/', views_shipments.TrackingEventCreateViewV2.as_view(), name='v2-add-tracking-event'),
]