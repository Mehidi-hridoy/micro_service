from rest_framework import serializers
from users.serializers import UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer
from shifting.serializers import ShipmentSerializer, TrackingEventSerializer

class ShipmentSerializerV1(serializers.ModelSerializer):
    """
    Version 1 of Shipment serializer with limited fields
    """
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    shipment_type_display = serializers.CharField(source='get_shipment_type_display', read_only=True)
    
    class Meta:
        model = ShipmentSerializer.Meta.model
        fields = [
            'shipment_id', 'tracking_number', 'shipment_type', 'shipment_type_display',
            'description', 'weight', 'pickup_address', 'delivery_address',
            'pickup_contact', 'delivery_contact', 'status', 'status_display',
            'current_location', 'pickup_date', 'estimated_delivery',
            'shipping_cost', 'total_amount', 'created_at'
        ]
        read_only_fields = ['shipment_id', 'tracking_number', 'created_at', 'total_amount']

class TrackingEventSerializerV1(serializers.ModelSerializer):
    """
    Version 1 of TrackingEvent serializer with limited fields
    """
    formatted_event_time = serializers.SerializerMethodField()
    
    class Meta:
        model = TrackingEventSerializer.Meta.model
        fields = [
            'event_type', 'description', 'location',
            'event_time', 'formatted_event_time'
        ]
        read_only_fields = ['event_time']
    
    def get_formatted_event_time(self, obj):
        return obj.event_time.strftime('%Y-%m-%d %H:%M:%S') if obj.event_time else None