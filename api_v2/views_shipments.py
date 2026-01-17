from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime
from shifting.models import Shipment, TrackingEvent
from shifting.serializers import (
    ShipmentSerializer, ShipmentCreateSerializer,
    ShipmentUpdateSerializer, TrackingEventSerializer,
    TrackingEventCreateSerializer
)

# ========== API VERSION 2 SHIPMENT VIEWS ==========

class ShipmentListViewV2(generics.ListCreateAPIView):
    """
    Version 2: List and create shipments with advanced filtering
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'shipment_type']
    search_fields = ['shipment_id', 'tracking_number', 'pickup_contact', 'delivery_contact']
    ordering_fields = ['created_at', 'pickup_date', 'estimated_delivery', 'total_amount']
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ShipmentCreateSerializer
        return ShipmentSerializer
    
    def get_queryset(self):
        user = self.request.user
        queryset = Shipment.objects.filter(tenant=user)
        
        # Apply additional filters from query params
        status = self.request.query_params.get('status')
        start_date = self.request.query_params.get('start_date')
        end_date = self.request.query_params.get('end_date')
        
        if status:
            queryset = queryset.filter(status=status)
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__gte=start_date)
            except ValueError:
                pass
        
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                queryset = queryset.filter(created_at__date__lte=end_date)
            except ValueError:
                pass
        
        return queryset.order_by('-created_at')
    
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

class ShipmentCreateViewV2(generics.CreateAPIView):
    """
    Version 2: Create shipment
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

class ShipmentDetailViewV2(generics.RetrieveUpdateDestroyAPIView):
    """
    Version 2: Shipment detail with update and delete
    """
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'shipment_id'
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Don't allow updating certain fields
        update_data = request.data.copy()
        restricted_fields = ['shipment_id', 'tracking_number', 'tenant', 'created_at']
        for field in restricted_fields:
            update_data.pop(field, None)
        
        serializer = ShipmentUpdateSerializer(
            instance, 
            data=update_data, 
            partial=partial
        )
        
        if serializer.is_valid():
            self.perform_update(serializer)
            
            # Log update event
            TrackingEvent.objects.create(
                shipment=instance,
                event_type='UPDATED',
                description='Shipment details updated',
                location=instance.current_location or 'System',
                remarks=f"Updated by {request.user.username}"
            )
            
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        
        # Soft delete - change status to cancelled
        instance.status = 'cancelled'
        instance.save()
        
        # Create cancellation event
        TrackingEvent.objects.create(
            shipment=instance,
            event_type='CANCELLED',
            description='Shipment cancelled',
            location='System',
            remarks=f"Cancelled by {request.user.username}"
        )
        
        return Response({
            'message': 'Shipment cancelled successfully',
            'shipment_id': instance.shipment_id
        }, status=status.HTTP_200_OK)

class ShipmentUpdateViewV2(generics.UpdateAPIView):
    """
    Version 2: Update shipment details
    """
    serializer_class = ShipmentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'shipment_id'
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)
    
    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        
        if serializer.is_valid():
            # Update shipment
            self.perform_update(serializer)
            
            # Create tracking event for update
            if serializer.validated_data.get('current_location'):
                TrackingEvent.objects.create(
                    shipment=instance,
                    event_type='LOCATION_UPDATE',
                    description=f"Location updated to {serializer.validated_data['current_location']}",
                    location=serializer.validated_data['current_location'],
                    remarks='Location updated by user'
                )
            
            return Response({
                'message': 'Shipment updated successfully',
                'shipment': ShipmentSerializer(instance).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ShipmentCancelViewV2(APIView):
    """
    Version 2: Cancel a shipment with enhanced validation
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
            
            # Check if pickup has already occurred
            if shipment.status in ['in_transit', 'out_for_delivery']:
                return Response({
                    'error': 'Cannot cancel shipment that is already in transit'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Update status
            old_status = shipment.status
            shipment.status = 'cancelled'
            shipment.save()
            
            # Create tracking event
            TrackingEvent.objects.create(
                shipment=shipment,
                event_type='CANCELLED',
                description='Shipment cancelled by user',
                location=shipment.current_location or 'System',
                remarks=f'Changed from {old_status} to cancelled'
            )
            
            # Refund logic (placeholder)
            refund_amount = shipment.total_amount * 0.8  # 80% refund
            if shipment.status == 'pending':
                refund_amount = shipment.total_amount  # 100% refund
            
            return Response({
                'message': 'Shipment cancelled successfully',
                'shipment_id': shipment.shipment_id,
                'new_status': shipment.status,
                'refund_amount': refund_amount,
                'refund_processed': False  # Placeholder for actual refund processing
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found'
            }, status=status.HTTP_404_NOT_FOUND)

class TrackingEventListViewV2(generics.ListCreateAPIView):
    """
    Version 2: List and create tracking events for a shipment
    """
    serializer_class = TrackingEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        shipment_id = self.kwargs.get('shipment_id')
        shipment = get_object_or_404(
            Shipment, 
            shipment_id=shipment_id,
            tenant=self.request.user
        )
        return TrackingEvent.objects.filter(shipment=shipment).order_by('-event_time')
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return TrackingEventCreateSerializer
        return TrackingEventSerializer
    
    def create(self, request, *args, **kwargs):
        shipment_id = self.kwargs.get('shipment_id')
        shipment = get_object_or_404(
            Shipment, 
            shipment_id=shipment_id,
            tenant=request.user
        )
        
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Update shipment status if event indicates status change
            event_type = serializer.validated_data.get('event_type', '').upper()
            if event_type in ['DELIVERED', 'IN_TRANSIT', 'OUT_FOR_DELIVERY']:
                shipment.status = event_type.lower()
                if event_type == 'DELIVERED':
                    shipment.actual_delivery = timezone.now()
                shipment.save()
            
            # Create tracking event
            tracking_event = serializer.save(shipment=shipment)
            
            return Response(
                TrackingEventSerializer(tracking_event).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TrackingEventCreateViewV2(generics.CreateAPIView):
    """
    Version 2: Create a new tracking event
    """
    serializer_class = TrackingEventCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        shipment_id = self.kwargs.get('shipment_id')
        shipment = get_object_or_404(
            Shipment, 
            shipment_id=shipment_id,
            tenant=self.request.user
        )
        serializer.save(shipment=shipment)