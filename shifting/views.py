from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from django.db import transaction, models
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from datetime import datetime, timedelta
import uuid
from .models import Shipment, TrackingEvent, TokenShift
from .serializers import (
    ShipmentSerializer, ShipmentCreateSerializer,
    ShipmentUpdateSerializer, TrackingEventSerializer,
    TokenShiftSerializer, TokenShiftRequestSerializer,
    ShipmentReportSerializer, FinancialReportSerializer
)

class ShipmentListView(generics.ListCreateAPIView):
    """
    List all shipments or create a new shipment
    """
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'shipment_type', 'tenant']
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

class ShipmentCreateView(generics.CreateAPIView):
    """
    Create a new shipment (alternate endpoint)
    """
    serializer_class = ShipmentCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    @transaction.atomic
    def perform_create(self, serializer):
        shipment = serializer.save(tenant=self.request.user)
        
        # Send notification (placeholder for actual notification system)
        self.send_shipment_created_notification(shipment)
    
    def send_shipment_created_notification(self, shipment):
        # This would integrate with your notifications service
        print(f"Notification: Shipment {shipment.shipment_id} created for {shipment.tenant.username}")

class ShipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a shipment
    """
    serializer_class = ShipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'shipment_id'
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)
    
    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {self.lookup_field: self.kwargs[self.lookup_field]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj
    
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

class ShipmentUpdateView(generics.UpdateAPIView):
    """
    Update shipment details
    """
    serializer_class = ShipmentUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'shipment_id'
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)

class ShipmentCancelView(APIView):
    """
    Cancel a shipment
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
            
            return Response({
                'message': 'Shipment cancelled successfully',
                'shipment_id': shipment.shipment_id,
                'new_status': shipment.status
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found'
            }, status=status.HTTP_404_NOT_FOUND)

class TrackingView(APIView):
    """
    Track a shipment by tracking number
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
                        'hours': time_diff.seconds // 3600
                    }
            
            return Response({
                'shipment': shipment_data,
                'tracking_events': events_data,
                'tracking_summary': {
                    'total_events': events.count(),
                    'current_status': shipment.status,
                    'current_location': shipment.current_location,
                    'estimated_delivery': shipment.estimated_delivery,
                    'estimated_time_remaining': estimated_time,
                    'is_delivered': shipment.status == 'delivered'
                }
            })
            
        except Shipment.DoesNotExist:
            return Response({
                'error': 'Shipment not found or access denied'
            }, status=status.HTTP_404_NOT_FOUND)

class TrackingEventListView(generics.ListCreateAPIView):
    """
    List all tracking events for a shipment or create new event
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

class TrackingEventCreateView(generics.CreateAPIView):
    """
    Create a new tracking event
    """
    serializer_class = TrackingEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_create(self, serializer):
        shipment_id = self.kwargs.get('shipment_id')
        shipment = get_object_or_404(
            Shipment, 
            shipment_id=shipment_id,
            tenant=self.request.user
        )
        serializer.save(shipment=shipment)

class TokenShiftRequestView(APIView):
    """
    Request token shifting to another service
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TokenShiftRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            target_service = serializer.validated_data['target_service']
            shift_reason = serializer.validated_data.get('shift_reason', '')
            
            # Generate new token for target service
            refresh = RefreshToken.for_user(user)
            new_token = str(refresh.access_token)
            
            # Add custom claims for target service
            import jwt
            try:
                decoded_token = jwt.decode(
                    new_token, 
                    options={"verify_signature": False}
                )
                decoded_token['service'] = target_service
                decoded_token['shifted_at'] = timezone.now().isoformat()
                
                # In production, you would re-sign with your secret
                # For now, we'll store the original token
            except:
                pass
            
            # Create token shift record
            token_shift = TokenShift.objects.create(
                user=user,
                original_token=str(request.auth),  # Current token
                shifted_token=new_token,
                source_service='shipping-service',
                target_service=target_service,
                shift_reason=shift_reason,
                token_type='access',
                expires_at=timezone.now() + timedelta(hours=1),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'shift_id': token_shift.id,
                'new_token': new_token,
                'target_service': target_service,
                'expires_at': token_shift.expires_at.isoformat(),
                'message': 'Token shifted successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

class TokenShiftHistoryView(generics.ListAPIView):
    """
    Get token shifting history for current user
    """
    serializer_class = TokenShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TokenShift.objects.filter(
            user=self.request.user
        ).order_by('-shifted_at')

class RevokeTokenShiftView(APIView):
    """
    Revoke a shifted token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, shift_id):
        try:
            token_shift = TokenShift.objects.get(
                id=shift_id,
                user=request.user,
                is_active=True
            )
            
            token_shift.is_active = False
            token_shift.save()
            
            return Response({
                'message': 'Shifted token revoked successfully',
                'shift_id': shift_id
            })
            
        except TokenShift.DoesNotExist:
            return Response({
                'error': 'Token shift record not found'
            }, status=status.HTTP_404_NOT_FOUND)

class ShipmentReportView(APIView):
    """
    Generate shipment reports
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        # Default to last 30 days
        if not start_date or not end_date:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        # Get shipments in date range
        shipments = Shipment.objects.filter(
            tenant=user,
            created_at__date__range=[start_date, end_date]
        )
        
        # Calculate statistics
        total_shipments = shipments.count()
        total_value = shipments.aggregate(
            total=models.Sum('total_amount')
        )['total'] or 0
        
        status_counts = shipments.values('status').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        type_counts = shipments.values('shipment_type').annotate(
            count=models.Count('id')
        ).order_by('-count')
        
        # Daily trend
        daily_trend = shipments.extra(
            {'date': "date(created_at)"}
        ).values('date').annotate(
            count=models.Count('id'),
            revenue=models.Sum('total_amount')
        ).order_by('date')
        
        return Response({
            'report_period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': (end_date - start_date).days + 1
            },
            'summary': {
                'total_shipments': total_shipments,
                'total_revenue': float(total_value),
                'average_shipment_value': float(total_value / total_shipments) if total_shipments > 0 else 0
            },
            'status_distribution': list(status_counts),
            'type_distribution': list(type_counts),
            'daily_trend': list(daily_trend),
            'generated_at': timezone.now().isoformat()
        })

class FinancialReportView(APIView):
    """
    Generate financial reports
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        month = request.query_params.get('month')
        year = request.query_params.get('year', timezone.now().year)
        
        # Get shipments for the period
        shipments = Shipment.objects.filter(tenant=user)
        
        if month:
            shipments = shipments.filter(
                created_at__year=year,
                created_at__month=month
            )
        else:
            shipments = shipments.filter(created_at__year=year)
        
        # Calculate financials
        financial_data = shipments.aggregate(
            total_revenue=models.Sum('total_amount'),
            total_cost=models.Sum('shipping_cost'),
            total_tax=models.Sum('tax_amount'),
            count=models.Count('id')
        )
        
        # Monthly breakdown if no specific month
        if not month:
            monthly_data = shipments.extra(
                {'month': "strftime('%Y-%m', created_at)"}
            ).values('month').annotate(
                revenue=models.Sum('total_amount'),
                shipments=models.Count('id')
            ).order_by('month')
        else:
            monthly_data = []
        
        return Response({
            'period': {
                'year': year,
                'month': month,
                'period': f"{year}-{month}" if month else f"{year}"
            },
            'financial_summary': {
                'total_shipments': financial_data['count'] or 0,
                'total_revenue': float(financial_data['total_revenue'] or 0),
                'total_shipping_cost': float(financial_data['total_cost'] or 0),
                'total_tax': float(financial_data['total_tax'] or 0),
                'net_revenue': float((financial_data['total_revenue'] or 0) - (financial_data['total_cost'] or 0))
            },
            'monthly_breakdown': list(monthly_data),
            'generated_at': timezone.now().isoformat()
        })
    
    