from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from shifting.models import Shipment, TrackingEvent
from shifting.serializers import ShipmentSerializer, ShipmentCreateSerializer

# ========== API VERSION 1 SHIPMENT VIEWS ==========

class ShipmentListViewV1(generics.ListCreateAPIView):
    """
    Version 1: List and create shipments (basic)
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ShipmentCreateSerializer
        return ShipmentSerializer
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user).order_by('-created_at')
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Set tenant to current user
            serializer.validated_data['tenant'] = request.user
            
            # Create shipment
            shipment = serializer.save()
            
            # Create initial tracking event
            TrackingEvent.objects.create(
                shipment=shipment,
                event_type='CREATED',
                description='Shipment created',
                location=shipment.pickup_address,
                remarks='Shipment registered in system'
            )
            
            return Response(
                ShipmentSerializer(shipment).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ShipmentCreateViewV1(generics.CreateAPIView):
    """
    Version 1: Create shipment
    """
    serializer_class = ShipmentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def perform_create(self, serializer):
        shipment = serializer.save(tenant=self.request.user)
        
        # Create initial tracking event
        TrackingEvent.objects.create(
            shipment=shipment,
            event_type='CREATED',
            description='Shipment created',
            location=shipment.pickup_address,
            remarks='Shipment registered in system'
        )

class ShipmentDetailViewV1(generics.RetrieveAPIView):
    """
    Version 1: Get shipment details
    """
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'shipment_id'
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)

class ShipmentCancelViewV1(APIView):
    """
    Version 1: Cancel a shipment
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            # Check if shipment can be cancelled
            if shipment.status in ['delivered', 'cancelled']:
                return Response({
                    'error': f'Cannot cancel shipment with status: {shipment.status}'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status
            shipment.status = 'cancelled'
            shipment.save()
            
            # Create tracking event
            TrackingEvent.objects.create(
                shipment=shipment,
                event_type='CANCELLED',
                description='Shipment cancelled by user',
                location=shipment.current_location or 'System',
                remarks='Shipment cancelled'
            )
            
            return Response({
                'message': 'Shipment cancelled successfully',
                'shipment_id': shipment.shipment_id,
                'new_status': shipment.status
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found'
            }, status=status.HTTP_404_NOT_FOUND)
        
        