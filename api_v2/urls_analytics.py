from django.urls import path
from . import views_analytics

urlpatterns = [
    path('dashboard/', views_analytics.DashboardStatsViewV2.as_view(), name='v2-analytics-dashboard'),
    path('summary/', views_analytics.AnalyticsSummaryViewV2.as_view(), name='v2-analytics-summary'),
    path('realtime/', views_analytics.RealTimeAnalyticsViewV2.as_view(), name='v2-realtime-analytics'),
]