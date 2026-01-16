from rest_framework import serializers
from .models import Shipment, TrackingEvent, ShippingRate

class TrackingEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrackingEvent
        fields = ['id', 'event_type', 'location', 'description', 'event_time']

class ShipmentSerializerV1(serializers.ModelSerializer):
    """Serializer for API v1 - Basic features"""
    tracking_events = TrackingEventSerializer(many=True, read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_number', 'sender_name', 'receiver_name',
            'status', 'created_at', 'tracking_events'
        ]
        read_only_fields = ['shipment_number', 'created_at']

class ShipmentSerializerV2(serializers.ModelSerializer):
    """Serializer for API v2 - More features"""
    tracking_events = TrackingEventSerializer(many=True, read_only=True)
    estimated_delivery = serializers.DateField(required=False)
    actual_delivery = serializers.DateField(read_only=True)
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_number', 'tenant_id', 
            'sender_name', 'sender_address',
            'receiver_name', 'receiver_address',
            'weight', 'dimensions', 'status',
            'estimated_delivery', 'actual_delivery',
            'created_at', 'updated_at', 'tracking_events'
        ]
        read_only_fields = ['shipment_number', 'tenant_id', 'created_at', 'updated_at']
    
    def create(self, validated_data):
        """Automatically set tenant_id from request"""
        request = self.context.get('request')
        if request and hasattr(request, 'tenant_id'):
            validated_data['tenant_id'] = request.tenant_id
        return super().create(validated_data)

class ShippingRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingRate
        fields = '__all__'
        read_only_fields = ['tenant_id']

class ShipmentCreateSerializer(serializers.Serializer):
    """Serializer for creating shipments with rate calculation"""
    sender_address = serializers.CharField()
    receiver_address = serializers.CharField()
    weight = serializers.DecimalField(max_digits=10, decimal_places=2)
    dimensions = serializers.CharField(required=False)
    
    def calculate_rate(self, tenant_id, data):
        """Calculate shipping rate based on locations and weight"""
        # Simplified rate calculation
        # In real app, this would query the ShippingRate model
        base_rate = 10.00
        weight_surcharge = float(data['weight']) * 2.5
        return base_rate + weight_surcharge