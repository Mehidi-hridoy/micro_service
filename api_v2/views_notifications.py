from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from notifications.models import Notification
from notifications.serializers import NotificationSerializer

# ========== API VERSION 2 NOTIFICATION VIEWS ==========

class NotificationListViewV2(generics.ListAPIView):
    """
    Version 2: List all notifications for current user
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user
        ).order_by('-created_at')

class UnreadNotificationCountViewV2(APIView):
    """
    Version 2: Get count of unread notifications
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False
        ).count()
        
        return Response({
            'unread_count': unread_count,
            'total_notifications': Notification.objects.filter(user=request.user).count()
        })

class MarkNotificationReadViewV2(APIView):
    """
    Version 2: Mark a notification as read
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, notification_id):
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user=request.user
            )
            
            notification.is_read = True
            notification.save()
            
            return Response({
                'message': 'Notification marked as read',
                'notification_id': notification_id
            })
            
        except Notification.DoesNotExist:
            return Response({
                'error': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)