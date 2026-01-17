from django.urls import path
from . import views

urlpatterns = [
    # Shipments
    path('shipments/', views.ShipmentListView.as_view(), name='shipment-list'),
    path('shipments/create/', views.ShipmentCreateView.as_view(), name='shipment-create'),
    path('shipments/<str:shipment_id>/', views.ShipmentDetailView.as_view(), name='shipment-detail'),
    path('shipments/<str:shipment_id>/update/', views.ShipmentUpdateView.as_view(), name='shipment-update'),
    path('shipments/<str:shipment_id>/cancel/', views.ShipmentCancelView.as_view(), name='shipment-cancel'),
    
    # Tracking
    path('tracking/<str:tracking_number>/', views.TrackingView.as_view(), name='track-shipment'),
    path('shipments/<str:shipment_id>/events/', views.TrackingEventListView.as_view(), name='tracking-events'),
    path('shipments/<str:shipment_id>/events/add/', views.TrackingEventCreateView.as_view(), name='add-tracking-event'),
    
    # Token Shifting
    path('token-shift/request/', views.TokenShiftRequestView.as_view(), name='token-shift-request'),
    path('token-shift/history/', views.TokenShiftHistoryView.as_view(), name='token-shift-history'),
    path('token-shift/<int:shift_id>/revoke/', views.RevokeTokenShiftView.as_view(), name='revoke-token-shift'),
    
    # Reports
    path('reports/shipments/', views.ShipmentReportView.as_view(), name='shipment-report'),
    path('reports/financial/', views.FinancialReportView.as_view(), name='financial-report'),
]