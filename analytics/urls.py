from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('dashboard/', views.DashboardStatsView.as_view(), name='analytics-dashboard'),
    
    # User Analytics
    path('user/', views.UserAnalyticsView.as_view(), name='user-analytics'),
    
    # Summary Reports
    path('summary/', views.AnalyticsSummaryView.as_view(), name='analytics-summary'),
    
    # Real-time Analytics
    path('realtime/', views.RealTimeAnalyticsView.as_view(), name='realtime-analytics'),
    
    # Export endpoints (to be implemented)
    path('export/csv/', views.AnalyticsSummaryView.as_view(), name='export-csv'),
    path('export/pdf/', views.AnalyticsSummaryView.as_view(), name='export-pdf'),
]