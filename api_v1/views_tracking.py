from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from shifting.models import Shipment, TrackingEvent
from shifting.serializers import ShipmentSerializer, TrackingEventSerializer

# ========== API VERSION 1 TRACKING VIEWS ==========

class TrackingViewV1(APIView):
    """
    Version 1: Track a shipment by tracking number
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
            
            return Response({
                'shipment': shipment_data,
                'tracking_events': events_data
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)