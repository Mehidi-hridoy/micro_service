from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from shifting.models import Shipment, TrackingEvent
from shifting.serializers import ShipmentSerializer, TrackingEventSerializer

# ========== API VERSION 2 TRACKING VIEWS ==========

class TrackingViewV2(APIView):
    """
    Version 2: Enhanced shipment tracking
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, tracking_number):
        try:
            shipment = Shipment.objects.get(
                tracking_number=tracking_number,
                tenant=request.user
            )
            
            # Get tracking events
            events = TrackingEvent.objects.filter(
                shipment=shipment
            ).order_by('event_time')
            
            shipment_data = ShipmentSerializer(shipment).data
            events_data = TrackingEventSerializer(events, many=True).data
            
            # Calculate estimated delivery time
            estimated_time = None
            if shipment.estimated_delivery:
                time_diff = shipment.estimated_delivery - timezone.now()
                if time_diff.total_seconds() > 0:
                    estimated_time = {
                        'days': time_diff.days,
                        'hours': time_diff.seconds // 3600,
                        'minutes': (time_diff.seconds % 3600) // 60
                    }
            
            # Check for delays
            is_delayed = False
            if shipment.estimated_delivery and shipment.status != 'delivered':
                is_delayed = timezone.now() > shipment.estimated_delivery
            
            return Response({
                'shipment': shipment_data,
                'tracking_events': events_data,
                'tracking_summary': {
                    'total_events': events.count(),
                    'current_status': shipment.status,
                    'current_location': shipment.current_location,
                    'estimated_delivery': shipment.estimated_delivery,
                    'estimated_time_remaining': estimated_time,
                    'is_delayed': is_delayed,
                    'is_delivered': shipment.status == 'delivered',
                    'delivery_date': shipment.actual_delivery if shipment.status == 'delivered' else None
                }
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)