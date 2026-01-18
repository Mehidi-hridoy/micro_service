from rest_framework import serializers
from django.utils import timezone
from .models import Shipment, TrackingEvent, TokenShift

class ShipmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'shipment_id', 'tenant', 'tracking_number', 'shipment_type',
            'description', 'dimensions', 'weight', 'pickup_address',
            'delivery_address', 'pickup_contact', 'delivery_contact',
            'status', 'current_location', 'shipping_cost', 'tax_amount',
            'total_amount', 'pickup_date', 'estimated_delivery',
            'actual_delivery', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['shipment_id', 'tracking_number', 'total_amount', 'created_at', 'updated_at']
    
    def validate(self, data):
        # Validate that estimated_delivery is after pickup_date
        if data.get('pickup_date') and data.get('estimated_delivery'):
            if data['estimated_delivery'] <= data['pickup_date']:
                raise serializers.ValidationError(
                    {'estimated_delivery': 'Estimated delivery must be after pickup date.'}
                )
        
        # Validate that actual_delivery is after pickup_date
        if data.get('pickup_date') and data.get('actual_delivery'):
            if data['actual_delivery'] <= data['pickup_date']:
                raise serializers.ValidationError(
                    {'actual_delivery': 'Actual delivery must be after pickup date.'}
                )
        
        # Validate weight is positive
        if 'weight' in data and data['weight'] <= 0:
            raise serializers.ValidationError(
                {'weight': 'Weight must be greater than zero.'}
            )
        
        # Validate shipping cost is non-negative
        if 'shipping_cost' in data and data['shipping_cost'] < 0:
            raise serializers.ValidationError(
                {'shipping_cost': 'Shipping cost cannot be negative.'}
            )
        
        # Validate tax amount is non-negative
        if 'tax_amount' in data and data['tax_amount'] < 0:
            raise serializers.ValidationError(
                {'tax_amount': 'Tax amount cannot be negative.'}
            )
        
        return data

class ShipmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'shipment_type', 'description', 'dimensions', 'weight',
            'pickup_address', 'delivery_address', 'pickup_contact',
            'delivery_contact', 'current_location', 'shipping_cost',
            'tax_amount', 'pickup_date', 'estimated_delivery', 'notes'
        ]
    
    def validate(self, data):
        # Call parent validation
        data = super().validate(data)
        
        # Additional validation for creation
        if 'pickup_date' in data and data['pickup_date'] < timezone.now():
            raise serializers.ValidationError(
                {'pickup_date': 'Pickup date cannot be in the past.'}
            )
        
        return data

class ShipmentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shipment
        fields = [
            'status', 'current_location', 'actual_delivery', 'notes'
        ]
    
    def validate(self, data):
        # Check if shipment can be updated
        shipment = self.instance
        
        if shipment.status == 'cancelled':
            raise serializers.ValidationError(
                {'status': 'Cannot update a cancelled shipment.'}
            )
        
        if shipment.status == 'delivered' and 'status' in data and data['status'] != 'delivered':
            raise serializers.ValidationError(
                {'status': 'Cannot change status of a delivered shipment.'}
            )
        
        # Validate actual_delivery
        if 'actual_delivery' in data:
            if data['actual_delivery'] < shipment.pickup_date:
                raise serializers.ValidationError(
                    {'actual_delivery': 'Actual delivery must be after pickup date.'}
                )
            if not data.get('status') or data.get('status') != 'delivered':
                data['status'] = 'delivered'
        
        return data

class ShipmentCancelSerializer(serializers.Serializer):
    cancellation_reason = serializers.CharField(max_length=500, required=False)
    
    def validate(self, data):
        shipment = self.context.get('shipment')
        
        if shipment.status == 'cancelled':
            raise serializers.ValidationError(
                {'detail': 'Shipment is already cancelled.'}
            )
        
        if shipment.status == 'delivered':
            raise serializers.ValidationError(
                {'detail': 'Cannot cancel a delivered shipment.'}
            )
        
        return data

class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = ['id', 'event_type', 'description', 'location', 'remarks', 'event_time']
        read_only_fields = ['id', 'event_time']
    
    def validate_event_type(self, value):
        valid_event_types = ['pickup', 'in_transit', 'delivered', 'delay', 'exception', 'custom']
        if value not in valid_event_types:
            raise serializers.ValidationError(
                f"Event type must be one of: {', '.join(valid_event_types)}"
            )
        return value

class TrackingEventCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = ['event_type', 'description', 'location', 'remarks']
    
    def validate(self, data):
        shipment = self.context.get('shipment')
        
        # Validate event_type based on shipment status
        if data.get('event_type') == 'delivered' and shipment.status == 'cancelled':
            raise serializers.ValidationError(
                {'event_type': 'Cannot mark a cancelled shipment as delivered.'}
            )
        
        return data

class TokenShiftSerializer(serializers.ModelSerializer):
    class Meta:
        model = TokenShift
        fields = [
            'id', 'original_token', 'shifted_token', 'source_service',
            'target_service', 'shift_reason', 'token_type', 'expires_at',
            'is_active', 'shifted_at', 'last_used', 'usage_count',
            'ip_address', 'user_agent'
        ]
        read_only_fields = [
            'id', 'shifted_token', 'shifted_at', 'last_used',
            'usage_count', 'ip_address', 'user_agent'
        ]
        extra_kwargs = {
            'original_token': {'write_only': True},
            'shifted_token': {'read_only': True}
        }
    
    def validate_expires_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                'Expiration date must be in the future.'
            )
        return value

class TokenShiftRequestSerializer(serializers.Serializer):
    original_token = serializers.CharField(write_only=True)
    source_service = serializers.CharField(max_length=50)
    target_service = serializers.CharField(max_length=50)
    shift_reason = serializers.CharField(max_length=200, required=False)
    token_type = serializers.ChoiceField(
        choices=[('access', 'Access Token'), ('refresh', 'Refresh Token')],
        default='access'
    )
    expires_in = serializers.IntegerField(
        min_value=60,
        max_value=86400,
        default=3600,
        help_text='Token validity in seconds (60-86400)'
    )
    
    def validate(self, data):
        # Validate that source and target are different
        if data['source_service'] == data['target_service']:
            raise serializers.ValidationError(
                {'source_service': 'Source and target services must be different.'}
            )
        return data

class TokenShiftHistorySerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = TokenShift
        fields = [
            'id', 'source_service', 'target_service', 'token_type',
            'expires_at', 'is_active', 'shifted_at', 'last_used',
            'usage_count', 'is_expired'
        ]
        read_only_fields = fields
    
    def get_is_expired(self, obj):
        return obj.is_expired()

class RevokeTokenShiftSerializer(serializers.Serializer):
    revocation_reason = serializers.CharField(max_length=200, required=False)

class ShipmentReportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    shipment_type = serializers.ChoiceField(
        choices=Shipment.SHIPMENT_TYPE,
        required=False
    )
    status = serializers.ChoiceField(
        choices=Shipment.STATUS_CHOICES,
        required=False
    )
    
    def validate(self, data):
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )
        return data

class FinancialReportSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    group_by = serializers.ChoiceField(
        choices=[('day', 'Day'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year')],
        default='month'
    )
    include_tax = serializers.BooleanField(default=True)
    
    def validate(self, data):
        if data['end_date'] < data['start_date']:
            raise serializers.ValidationError(
                {'end_date': 'End date must be after start date.'}
            )
        return data

# Additional serializers for nested representations
class ShipmentDetailSerializer(ShipmentSerializer):
    tracking_events = TrackingEventSerializer(many=True, read_only=True)
    
    class Meta(ShipmentSerializer.Meta):
        fields = ShipmentSerializer.Meta.fields + ['tracking_events']

class TrackingViewSerializer(serializers.ModelSerializer):
    tracking_events = TrackingEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'shipment_id', 'tracking_number', 'status', 'current_location',
            'pickup_address', 'delivery_address', 'estimated_delivery',
            'actual_delivery', 'pickup_date', 'tracking_events'
        ]