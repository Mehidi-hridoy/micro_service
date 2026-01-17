from django.urls import path
from . import views_shifting

urlpatterns = [
    path('request/', views_shifting.TokenShiftRequestViewV2.as_view(), name='v2-token-shift-request'),
    path('history/', views_shifting.TokenShiftHistoryViewV2.as_view(), name='v2-token-shift-history'),
    path('<int:shift_id>/revoke/', views_shifting.RevokeTokenShiftViewV2.as_view(), name='v2-revoke-token-shift'),
]