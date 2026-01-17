from django.urls import path
from . import views_shipments

urlpatterns = [
    path('', views_shipments.ShipmentListViewV1.as_view(), name='v1-shipment-list'),
    path('create/', views_shipments.ShipmentCreateViewV1.as_view(), name='v1-shipment-create'),
    path('<str:shipment_id>/', views_shipments.ShipmentDetailViewV1.as_view(), name='v1-shipment-detail'),
    path('<str:shipment_id>/cancel/', views_shipments.ShipmentCancelViewV1.as_view(), name='v1-shipment-cancel'),
]