from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views_auth

urlpatterns = [
    path('register/', views_auth.UserRegistrationViewV2.as_view(), name='v2-register'),
    path('login/', views_auth.UserLoginViewV2.as_view(), name='v2-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='v2-token-refresh'),
    path('logout/', views_auth.UserLogoutViewV2.as_view(), name='v2-logout'),
    path('profile/', views_auth.UserProfileViewV2.as_view(), name='v2-profile'),
    path('profile/update/', views_auth.UserUpdateViewV2.as_view(), name='v2-profile-update'),
    path('profile/change-password/', views_auth.ChangePasswordViewV2.as_view(), name='v2-change-password'),
    path('sessions/', views_auth.UserSessionListViewV2.as_view(), name='v2-sessions'),
]
from django.urls import path
from . import views

urlpatterns = [
    # Auth endpoints
    path('auth/register/', views.UserRegistrationViewV2.as_view(), name='v2-register'),
    path('auth/login/', views.UserLoginViewV2.as_view(), name='v2-login'),
    path('auth/profile/', views.UserProfileViewV2.as_view(), name='v2-profile'),
    path('auth/profile/update/', views.UserUpdateViewV2.as_view(), name='v2-profile-update'),
    path('auth/change-password/', views.ChangePasswordViewV2.as_view(), name='v2-change-password'),
    
    # Shipment endpoints
    path('shipments/', views.ShipmentListViewV2.as_view(), name='v2-shipment-list'),
    path('shipments/create/', views.ShipmentCreateViewV2.as_view(), name='v2-shipment-create'),
    path('shipments/<str:shipment_id>/', views.ShipmentDetailViewV2.as_view(), name='v2-shipment-detail'),
    path('shipments/<str:shipment_id>/update/', views.ShipmentUpdateViewV2.as_view(), name='v2-shipment-update'),
    path('shipments/<str:shipment_id>/cancel/', views.ShipmentCancelViewV2.as_view(), name='v2-shipment-cancel'),
    path('shipments/<str:shipment_id>/events/', views.TrackingEventListViewV2.as_view(), name='v2-tracking-events'),
    
    # Tracking endpoints
    path('tracking/<str:tracking_number>/', views.TrackingViewV2.as_view(), name='v2-track-shipment'),
    
    # Token shifting
    path('shifting/request/', views.TokenShiftRequestViewV2.as_view(), name='v2-token-shift-request'),
    path('shifting/history/', views.TokenShiftHistoryViewV2.as_view(), name='v2-token-shift-history'),
    
    # Analytics
    path('analytics/dashboard/', views.DashboardStatsViewV2.as_view(), name='v2-analytics-dashboard'),
    
    # Reports
    path('reports/shipments/', views.ShipmentReportViewV2.as_view(), name='v2-shipment-report'),
]