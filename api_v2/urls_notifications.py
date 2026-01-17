from django.urls import path
from . import views_notifications

urlpatterns = [
    path('', views_notifications.NotificationListViewV2.as_view(), name='v2-notification-list'),
    path('unread-count/', views_notifications.UnreadNotificationCountViewV2.as_view(), name='v2-unread-count'),
    path('<int:notification_id>/mark-read/', views_notifications.MarkNotificationReadViewV2.as_view(), name='v2-mark-read'),
]