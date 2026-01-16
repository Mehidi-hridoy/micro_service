from rest_framework import viewsets, status, permissions, generics
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Q
from .models import Shipment, TrackingEvent, ShippingRate
from .serializers import (
    ShipmentSerializerV1, ShipmentSerializerV2,
    TrackingEventSerializer, ShippingRateSerializer,
    ShipmentCreateSerializer
)

class BaseShipmentViewSet(viewsets.ModelViewSet):
    """Base shipment viewset with tenant filtering"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter shipments by tenant"""
        queryset = Shipment.objects.all()
        
        # Filter by tenant if tenant_id is set
        if hasattr(self.request, 'tenant_id') and self.request.tenant_id:
            queryset = queryset.filter(tenant_id=self.request.tenant_id)
        
        # Additional filtering
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(shipment_number__icontains=search) |
                Q(sender_name__icontains=search) |
                Q(receiver_name__icontains=search)
            )
        
        return queryset

class ShipmentViewSetV1(BaseShipmentViewSet):
    """API v1 - Basic shipment operations"""
    serializer_class = ShipmentSerializerV1
    
    def get_serializer_class(self):
        return ShipmentSerializerV1
    
    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update shipment status (v1)"""
        shipment = self.get_object()
        new_status = request.data.get('status')
        
        if new_status in dict(Shipment.SHIPMENT_STATUS):
            shipment.status = new_status
            shipment.save()
            return Response({'status': 'updated'})
        
        return Response({'error': 'Invalid status'}, status=400)

class ShipmentViewSetV2(BaseShipmentViewSet):
    """API v2 - Enhanced shipment operations"""
    serializer_class = ShipmentSerializerV2
    
    def get_serializer_class(self):
        return ShipmentSerializerV2
    
    @action(detail=True, methods=['post'])
    def add_tracking_event(self, request, pk=None):
        """Add tracking event to shipment"""
        shipment = self.get_object()
        serializer = TrackingEventSerializer(data=request.data)
        
        if serializer.is_valid():
            serializer.save(shipment=shipment)
            return Response(serializer.data)
        
        return Response(serializer.errors, status=400)
    
    @action(detail=True, methods=['get'])
    def calculate_rate(self, request, pk=None):
        """Calculate shipping rate"""
        shipment = self.get_object()
        # Rate calculation logic here
        return Response({'estimated_rate': 25.50})
    
    @action(detail=False, methods=['post'])
    def bulk_create(self, request):
        """Bulk create shipments"""
        serializer = self.get_serializer(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)
    
    @action(detail=False, methods=['get'])
    def analytics(self, request):
        """Get shipment analytics"""
        queryset = self.get_queryset()
        
        analytics = {
            'total_shipments': queryset.count(),
            'by_status': dict(queryset.values_list('status').annotate(models.Count('id'))),
            'pending': queryset.filter(status='pending').count(),
            'in_transit': queryset.filter(status='in_transit').count(),
            'delivered': queryset.filter(status='delivered').count(),
        }
        
        return Response(analytics)

class TrackingEventViewSet(viewsets.ModelViewSet):
    """Tracking event management"""
    serializer_class = TrackingEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TrackingEvent.objects.filter(
            shipment__tenant_id=self.request.tenant_id
        )

class ShippingRateViewSet(viewsets.ModelViewSet):
    """Shipping rate management"""
    serializer_class = ShippingRateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return ShippingRate.objects.filter(tenant_id=self.request.tenant_id)
    
    def perform_create(self, serializer):
        serializer.save(tenant_id=self.request.tenant_id)

class CalculateRateAPI(APIView):
    """API for calculating shipping rates"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ShipmentCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Calculate rate based on tenant
            rate = serializer.calculate_rate(request.tenant_id, serializer.validated_data)
            
            return Response({
                'rate': rate,
                'currency': 'USD',
                'breakdown': {
                    'base_rate': 10.00,
                    'weight_surcharge': rate - 10.00
                }
            })
        
        return Response(serializer.errors, status=400)
    
from django.db.models import Q, Count  # Add Count import


# Add missing function in analytics action
def get_queryset_values(self):
    """Helper method for analytics"""
    queryset = self.get_queryset()
    return queryset.values('status').annotate(count=Count('id'))

