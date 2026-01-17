from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from .models import Shipment, TrackingEvent, TokenShift
import re

User = get_user_model()

class ShipmentCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating new shipments
    """
    pickup_contact_phone = serializers.CharField(
        source='pickup_phone',
        max_length=20,
        required=True,
        help_text="Pickup contact phone number"
    )
    delivery_contact_phone = serializers.CharField(
        source='delivery_phone',
        max_length=20,
        required=True,
        help_text="Delivery contact phone number"
    )
    
    class Meta:
        model = Shipment
        fields = [
            'shipment_type', 'description', 'weight', 'dimensions',
            'declared_value', 'pickup_address', 'delivery_address',
            'pickup_contact', 'delivery_contact', 'pickup_contact_phone',
            'delivery_contact_phone', 'pickup_date', 'estimated_delivery',
            'shipping_cost', 'tax_amount', 'notes'
        ]
        extra_kwargs = {
            'pickup_date': {'required': False},
            'estimated_delivery': {'required': False},
            'shipping_cost': {'required': False, 'default': 0},
            'tax_amount': {'required': False, 'default': 0},
        }
    
    def validate_weight(self, value):
        """Validate weight is positive"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        if value > 1000:  # 1000 kg limit
            raise serializers.ValidationError("Weight cannot exceed 1000 kg")
        return value
    
    def validate_declared_value(self, value):
        """Validate declared value"""
        if value is not None and value <= 0:
            raise serializers.ValidationError("Declared value must be positive")
        if value and value > 1000000:  # 1 million limit
            raise serializers.ValidationError("Declared value cannot exceed 1,000,000")
        return value
    
    def validate_pickup_contact_phone(self, value):
        """Validate phone number format"""
        return self._validate_phone_number(value)
    
    def validate_delivery_contact_phone(self, value):
        """Validate phone number format"""
        return self._validate_phone_number(value)
    
    def _validate_phone_number(self, phone):
        """Validate phone number format"""
        # Basic phone validation - can be enhanced based on country
        phone = str(phone).strip()
        
        # Remove any non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        if not cleaned:
            raise serializers.ValidationError("Invalid phone number format")
        
        if len(cleaned) < 10:
            raise serializers.ValidationError("Phone number is too short")
        
        if len(cleaned) > 15:
            raise serializers.ValidationError("Phone number is too long")
        
        return phone
    
    def validate_pickup_address(self, value):
        """Validate address length"""
        if len(value) < 10:
            raise serializers.ValidationError("Address is too short. Please provide a complete address.")
        if len(value) > 500:
            raise serializers.ValidationError("Address is too long (max 500 characters).")
        return value
    
    def validate_delivery_address(self, value):
        """Validate address length"""
        if len(value) < 10:
            raise serializers.ValidationError("Address is too short. Please provide a complete address.")
        if len(value) > 500:
            raise serializers.ValidationError("Address is too long (max 500 characters).")
        return value
    
    def validate(self, data):
        """Additional validation for the entire shipment"""
        # Ensure pickup date is not in the past
        pickup_date = data.get('pickup_date')
        if pickup_date and pickup_date < timezone.now():
            raise serializers.ValidationError({
                'pickup_date': 'Pickup date cannot be in the past'
            })
        
        # Ensure estimated delivery is after pickup date
        estimated_delivery = data.get('estimated_delivery')
        if pickup_date and estimated_delivery:
            if estimated_delivery <= pickup_date:
                raise serializers.ValidationError({
                    'estimated_delivery': 'Estimated delivery must be after pickup date'
                })
        
        # Calculate total amount
        shipping_cost = data.get('shipping_cost', 0) or 0
        tax_amount = data.get('tax_amount', 0) or 0
        data['total_amount'] = shipping_cost + tax_amount
        
        return data

class ShipmentUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for updating existing shipments
    """
    current_location = serializers.CharField(
        required=False,
        help_text="Current location of the shipment"
    )
    
    class Meta:
        model = Shipment
        fields = [
            'description', 'weight', 'dimensions', 'declared_value',
            'pickup_address', 'delivery_address', 'pickup_contact',
            'delivery_contact', 'pickup_phone', 'delivery_phone',
            'pickup_date', 'estimated_delivery', 'current_location',
            'shipping_cost', 'tax_amount', 'notes', 'metadata'
        ]
        read_only_fields = ['shipment_id', 'tracking_number', 'tenant', 'created_at']
        extra_kwargs = {
            'shipping_cost': {'required': False},
            'tax_amount': {'required': False},
            'notes': {'required': False},
            'metadata': {'required': False},
        }
    
    def validate(self, data):
        """Validate update data"""
        # If status is being updated to delivered, require actual_delivery
        if self.instance and 'status' in data:
            if data['status'] == 'delivered' and not data.get('actual_delivery'):
                data['actual_delivery'] = timezone.now()
        
        # Recalculate total amount if cost fields are updated
        if 'shipping_cost' in data or 'tax_amount' in data:
            shipping_cost = data.get('shipping_cost', self.instance.shipping_cost)
            tax_amount = data.get('tax_amount', self.instance.tax_amount)
            data['total_amount'] = shipping_cost + tax_amount
        
        return data

class ShipmentSerializer(serializers.ModelSerializer):
    """
    Complete serializer for Shipment model with all fields
    """
    tenant = serializers.StringRelatedField()
    tenant_id = serializers.IntegerField(source='tenant.id')
    tenant_username = serializers.CharField(source='tenant.username')
    tenant_company = serializers.CharField(source='tenant.company_name')
    
    # Calculated fields
    shipment_type_display = serializers.CharField(source='get_shipment_type_display')
    status_display = serializers.CharField(source='get_status_display')
    days_in_transit = serializers.SerializerMethodField()
    is_overdue = serializers.SerializerMethodField()
    formatted_pickup_date = serializers.SerializerMethodField()
    formatted_estimated_delivery = serializers.SerializerMethodField()
    formatted_actual_delivery = serializers.SerializerMethodField()
    formatted_created_at = serializers.SerializerMethodField()
    
    # Tracking summary
    tracking_events_count = serializers.SerializerMethodField()
    last_tracking_event = serializers.SerializerMethodField()
    
    class Meta:
        model = Shipment
        fields = [
            # Basic Info
            'id', 'shipment_id', 'tenant', 'tenant_id', 'tenant_username', 'tenant_company',
            
            # Shipment Details
            'shipment_type', 'shipment_type_display', 'description', 'weight', 'dimensions',
            'declared_value',
            
            # Address Information
            'pickup_address', 'delivery_address', 'pickup_contact', 'delivery_contact',
            'pickup_phone', 'delivery_phone',
            
            # Status and Tracking
            'status', 'status_display', 'tracking_number', 'current_location',
            
            # Dates
            'pickup_date', 'estimated_delivery', 'actual_delivery', 'created_at',
            'formatted_pickup_date', 'formatted_estimated_delivery',
            'formatted_actual_delivery', 'formatted_created_at',
            
            # Calculated Fields
            'days_in_transit', 'is_overdue',
            
            # Financial
            'shipping_cost', 'tax_amount', 'total_amount',
            
            # Metadata
            'notes', 'metadata',
            
            # Tracking Summary
            'tracking_events_count', 'last_tracking_event',
            
            # System Fields
            'updated_at'
        ]
        read_only_fields = [
            'id', 'shipment_id', 'tracking_number', 'tenant', 'created_at',
            'updated_at', 'total_amount'
        ]
    
    def get_days_in_transit(self, obj):
        """Calculate days in transit"""
        if obj.status == 'delivered' and obj.actual_delivery and obj.pickup_date:
            return (obj.actual_delivery - obj.pickup_date).days
        elif obj.pickup_date:
            return (timezone.now() - obj.pickup_date).days
        return 0
    
    def get_is_overdue(self, obj):
        """Check if shipment is overdue"""
        if obj.estimated_delivery and obj.status not in ['delivered', 'cancelled']:
            return timezone.now() > obj.estimated_delivery
        return False
    
    def get_formatted_pickup_date(self, obj):
        return obj.pickup_date.strftime('%Y-%m-%d %H:%M') if obj.pickup_date else None
    
    def get_formatted_estimated_delivery(self, obj):
        return obj.estimated_delivery.strftime('%Y-%m-%d %H:%M') if obj.estimated_delivery else None
    
    def get_formatted_actual_delivery(self, obj):
        return obj.actual_delivery.strftime('%Y-%m-%d %H:%M') if obj.actual_delivery else None
    
    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if obj.created_at else None
    
    def get_tracking_events_count(self, obj):
        return obj.tracking_events.count()
    
    def get_last_tracking_event(self, obj):
        last_event = obj.tracking_events.order_by('-event_time').first()
        if last_event:
            return {
                'event_type': last_event.event_type,
                'description': last_event.description,
                'location': last_event.location,
                'event_time': last_event.event_time.strftime('%Y-%m-%d %H:%M:%S')
            }
        return None

class ShipmentListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for listing shipments
    """
    status_display = serializers.CharField(source='get_status_display')
    shipment_type_display = serializers.CharField(source='get_shipment_type_display')
    is_overdue = serializers.SerializerMethodField()
    days_since_creation = serializers.SerializerMethodField()
    
    class Meta:
        model = Shipment
        fields = [
            'id', 'shipment_id', 'tracking_number', 'shipment_type',
            'shipment_type_display', 'status', 'status_display',
            'pickup_contact', 'delivery_contact', 'current_location',
            'pickup_date', 'estimated_delivery', 'total_amount',
            'is_overdue', 'days_since_creation', 'created_at'
        ]
    
    def get_is_overdue(self, obj):
        if obj.estimated_delivery and obj.status not in ['delivered', 'cancelled']:
            return timezone.now() > obj.estimated_delivery
        return False
    
    def get_days_since_creation(self, obj):
        return (timezone.now() - obj.created_at).days

class TrackingEventSerializer(serializers.ModelSerializer):
    """
    Serializer for TrackingEvent model
    """
    shipment_id = serializers.CharField(source='shipment.shipment_id', read_only=True)
    shipment_tracking = serializers.CharField(source='shipment.tracking_number', read_only=True)
    formatted_event_time = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    event_icon = serializers.SerializerMethodField()
    
    class Meta:
        model = TrackingEvent
        fields = [
            'id', 'shipment', 'shipment_id', 'shipment_tracking',
            'event_type', 'description', 'location', 'remarks',
            'event_time', 'formatted_event_time', 'time_ago',
            'event_icon', 'metadata'
        ]
        read_only_fields = ['id', 'event_time']
        extra_kwargs = {
            'shipment': {'write_only': True},
            'metadata': {'required': False, 'default': dict},
        }
    
    def validate_event_type(self, value):
        """Validate event type"""
        allowed_events = [
            'CREATED', 'PICKUP_SCHEDULED', 'PICKED_UP', 'IN_TRANSIT',
            'ARRIVED_AT_HUB', 'DEPARTED_FROM_HUB', 'OUT_FOR_DELIVERY',
            'DELIVERY_ATTEMPTED', 'DELIVERED', 'CANCELLED', 'DELAYED',
            'EXCEPTION', 'HOLD', 'RETURNED', 'DAMAGED', 'LOST',
            'LOCATION_UPDATE', 'STATUS_CHANGE', 'NOTE_ADDED'
        ]
        
        if value.upper() not in allowed_events:
            raise serializers.ValidationError(
                f"Invalid event type. Allowed types: {', '.join(allowed_events)}"
            )
        
        return value.upper()
    
    def validate(self, data):
        """Validate tracking event data"""
        # If event_type is DELIVERED, automatically set location to delivery address
        if data.get('event_type') == 'DELIVERED' and not data.get('location'):
            data['location'] = data['shipment'].delivery_address
        
        return data
    
    def get_formatted_event_time(self, obj):
        return obj.event_time.strftime('%Y-%m-%d %H:%M:%S') if obj.event_time else None
    
    def get_time_ago(self, obj):
        if not obj.event_time:
            return None
        
        now = timezone.now()
        diff = now - obj.event_time
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def get_event_icon(self, obj):
        """Return appropriate icon based on event type"""
        icon_map = {
            'CREATED': '📦',
            'PICKUP_SCHEDULED': '📅',
            'PICKED_UP': '🚚',
            'IN_TRANSIT': '🚛',
            'ARRIVED_AT_HUB': '🏢',
            'DEPARTED_FROM_HUB': '🏢➡️',
            'OUT_FOR_DELIVERY': '📮',
            'DELIVERY_ATTEMPTED': '🔄',
            'DELIVERED': '✅',
            'CANCELLED': '❌',
            'DELAYED': '⏰',
            'EXCEPTION': '⚠️',
            'HOLD': '⏸️',
            'RETURNED': '↩️',
            'DAMAGED': '💔',
            'LOST': '🔍',
            'LOCATION_UPDATE': '📍',
            'STATUS_CHANGE': '🔄',
            'NOTE_ADDED': '📝'
        }
        return icon_map.get(obj.event_type, '📋')

class TrackingEventCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating tracking events
    """
    class Meta:
        model = TrackingEvent
        fields = ['event_type', 'description', 'location', 'remarks', 'metadata']
    
    def validate(self, data):
        """Additional validation for tracking events"""
        # Ensure description is provided
        if not data.get('description'):
            data['description'] = f"Shipment {data.get('event_type', 'updated').replace('_', ' ').title()}"
        
        # Ensure location is provided for certain events
        location_required_events = ['LOCATION_UPDATE', 'ARRIVED_AT_HUB', 'DEPARTED_FROM_HUB']
        if data.get('event_type') in location_required_events and not data.get('location'):
            raise serializers.ValidationError({
                'location': f'Location is required for {data["event_type"]} events'
            })
        
        return data

class TokenShiftSerializer(serializers.ModelSerializer):
    """
    Serializer for TokenShift model
    """
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    # Calculated fields
    is_expired = serializers.SerializerMethodField()
    token_preview = serializers.SerializerMethodField()
    formatted_shifted_at = serializers.SerializerMethodField()
    formatted_expires_at = serializers.SerializerMethodField()
    formatted_last_used = serializers.SerializerMethodField()
    time_until_expiry = serializers.SerializerMethodField()
    
    class Meta:
        model = TokenShift
        fields = [
            'id', 'user', 'user_id', 'username',
            'original_token', 'shifted_token', 'source_service', 'target_service',
            'shift_reason', 'token_type', 'expires_at', 'is_active',
            'shifted_at', 'last_used', 'usage_count', 'ip_address', 'user_agent',
            
            # Calculated fields
            'is_expired', 'token_preview', 'formatted_shifted_at',
            'formatted_expires_at', 'formatted_last_used', 'time_until_expiry'
        ]
        read_only_fields = [
            'id', 'user', 'shifted_at', 'last_used', 'usage_count',
            'ip_address', 'user_agent', 'is_expired'
        ]
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_token_preview(self, obj):
        """Show a preview of the token (first and last few chars)"""
        token = obj.shifted_token or ''
        if len(token) > 20:
            return f"{token[:10]}...{token[-10:]}"
        return token
    
    def get_formatted_shifted_at(self, obj):
        return obj.shifted_at.strftime('%Y-%m-%d %H:%M:%S') if obj.shifted_at else None
    
    def get_formatted_expires_at(self, obj):
        return obj.expires_at.strftime('%Y-%m-%d %H:%M:%S') if obj.expires_at else None
    
    def get_formatted_last_used(self, obj):
        return obj.last_used.strftime('%Y-%m-%d %H:%M:%S') if obj.last_used else None
    
    def get_time_until_expiry(self, obj):
        if not obj.expires_at or obj.is_expired():
            return "Expired"
        
        now = timezone.now()
        diff = obj.expires_at - now
        
        if diff.days > 0:
            return f"{diff.days}d {diff.seconds // 3600}h"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h {diff.seconds % 3600 // 60}m"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m {diff.seconds % 60}s"
        else:
            return f"{diff.seconds}s"
    
    def validate(self, data):
        """Validate token shift data"""
        # Ensure target service is different from source service
        if data.get('source_service') == data.get('target_service'):
            raise serializers.ValidationError({
                'target_service': 'Target service must be different from source service'
            })
        
        # Set expiry time if not provided
        if not data.get('expires_at'):
            data['expires_at'] = timezone.now() + timedelta(hours=1)
        
        # Ensure expiry is in the future
        if data.get('expires_at') and data['expires_at'] <= timezone.now():
            raise serializers.ValidationError({
                'expires_at': 'Expiry time must be in the future'
            })
        
        return data

class TokenShiftRequestSerializer(serializers.Serializer):
    """
    Serializer for requesting token shift
    """
    target_service = serializers.CharField(
        max_length=50,
        required=True,
        help_text="Target service to shift token to"
    )
    shift_reason = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
        help_text="Reason for token shift"
    )
    expires_in = serializers.IntegerField(
        min_value=300,  # 5 minutes
        max_value=86400,  # 24 hours
        default=3600,  # 1 hour
        required=False,
        help_text="Token expiry in seconds"
    )
    
    def validate_target_service(self, value):
        """Validate target service"""
        allowed_services = [
            'user-service', 'shipping-service', 'tracking-service',
            'payment-service', 'analytics-service', 'notification-service',
            'api-gateway', 'admin-panel'
        ]
        
        if value not in allowed_services:
            raise serializers.ValidationError(
                f"Invalid target service. Allowed: {', '.join(allowed_services)}"
            )
        
        return value
    
    def validate_expires_in(self, value):
        """Validate expiry time"""
        if value < 300:
            raise serializers.ValidationError("Token must expire in at least 5 minutes")
        if value > 86400:
            raise serializers.ValidationError("Token cannot expire in more than 24 hours")
        return value

class ShipmentReportSerializer(serializers.Serializer):
    """
    Serializer for shipment reports
    """
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    status = serializers.CharField(required=False)
    shipment_type = serializers.CharField(required=False)
    group_by = serializers.ChoiceField(
        choices=[
            ('day', 'Day'),
            ('week', 'Week'),
            ('month', 'Month'),
            ('status', 'Status'),
            ('type', 'Shipment Type')
        ],
        default='day'
    )
    format = serializers.ChoiceField(
        choices=['json', 'csv', 'pdf'],
        default='json'
    )
    include_details = serializers.BooleanField(default=False)
    
    def validate(self, data):
        """Validate report parameters"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date:
            if start_date > end_date:
                raise serializers.ValidationError({
                    'start_date': 'Start date cannot be after end date'
                })
            
            # Limit to 365 days
            if (end_date - start_date).days > 365:
                raise serializers.ValidationError({
                    'end_date': 'Date range cannot exceed 365 days'
                })
        
        return data
    
    def get_default_dates(self):
        """Get default date range (last 30 days)"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)
        return start_date, end_date

class FinancialReportSerializer(serializers.Serializer):
    """
    Serializer for financial reports
    """
    period = serializers.ChoiceField(
        choices=[
            ('daily', 'Daily'),
            ('weekly', 'Weekly'),
            ('monthly', 'Monthly'),
            ('quarterly', 'Quarterly'),
            ('yearly', 'Yearly'),
            ('custom', 'Custom')
        ],
        default='monthly'
    )
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)
    include_breakdown = serializers.BooleanField(default=True)
    currency = serializers.CharField(default='USD', max_length=3)
    
    def validate(self, data):
        """Validate financial report parameters"""
        period = data.get('period')
        
        if period == 'custom':
            if not data.get('start_date') or not data.get('end_date'):
                raise serializers.ValidationError({
                    'start_date': 'Start date and end date are required for custom period',
                    'end_date': 'Start date and end date are required for custom period'
                })
        
        elif period == 'monthly':
            if not data.get('year') or not data.get('month'):
                # Default to current month
                now = timezone.now()
                data['year'] = now.year
                data['month'] = now.month
        
        elif period == 'yearly':
            if not data.get('year'):
                data['year'] = timezone.now().year
        
        return data

class ShipmentFilterSerializer(serializers.Serializer):
    """
    Serializer for filtering shipments
    """
    status = serializers.CharField(required=False)
    shipment_type = serializers.CharField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    search = serializers.CharField(required=False)
    sort_by = serializers.ChoiceField(
        choices=[
            ('created_at', 'Creation Date'),
            ('pickup_date', 'Pickup Date'),
            ('estimated_delivery', 'Estimated Delivery'),
            ('total_amount', 'Total Amount'),
            ('status', 'Status')
        ],
        default='created_at'
    )
    sort_order = serializers.ChoiceField(
        choices=['asc', 'desc'],
        default='desc'
    )
    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(min_value=1, max_value=100, default=20)
    
    def validate(self, data):
        """Validate filter parameters"""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError({
                    'start_date': 'Start date cannot be after end date'
                })
        
        return data

class BulkShipmentCreateSerializer(serializers.Serializer):
    """
    Serializer for creating multiple shipments at once
    """
    shipments = ShipmentCreateSerializer(many=True)
    notification_preference = serializers.ChoiceField(
        choices=['email', 'sms', 'none'],
        default='email'
    )
    
    def validate_shipments(self, value):
        """Validate bulk shipments"""
        if len(value) > 100:
            raise serializers.ValidationError("Cannot create more than 100 shipments at once")
        
        # Check for duplicate tracking numbers
        tracking_numbers = []
        for shipment in value:
            # Generate tracking number for validation
            import uuid
            tracking_num = f"TRK{uuid.uuid4().hex[:12].upper()}"
            if tracking_num in tracking_numbers:
                raise serializers.ValidationError("Duplicate tracking numbers detected")
            tracking_numbers.append(tracking_num)
        
        return value

class ShipmentStatusUpdateSerializer(serializers.Serializer):
    """
    Serializer for updating shipment status
    """
    status = serializers.ChoiceField(
        choices=[
            ('pending', 'Pending'),
            ('pickup_scheduled', 'Pickup Scheduled'),
            ('in_transit', 'In Transit'),
            ('out_for_delivery', 'Out for Delivery'),
            ('delivered', 'Delivered'),
            ('cancelled', 'Cancelled'),
            ('delayed', 'Delayed')
        ],
        required=True
    )
    location = serializers.CharField(
        required=False,
        help_text="Current location (required for in_transit status)"
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    actual_delivery = serializers.DateTimeField(required=False)
    
    def validate(self, data):
        """Validate status update"""
        status = data.get('status')
        
        # Require location for in_transit status
        if status == 'in_transit' and not data.get('location'):
            raise serializers.ValidationError({
                'location': 'Location is required for in_transit status'
            })
        
        # Set actual_delivery for delivered status
        if status == 'delivered' and not data.get('actual_delivery'):
            data['actual_delivery'] = timezone.now()
        
        return data

class TrackingNumberSerializer(serializers.Serializer):
    """
    Serializer for tracking number validation
    """
    tracking_number = serializers.CharField(
        max_length=100,
        required=True,
        help_text="Shipment tracking number"
    )
    
    def validate_tracking_number(self, value):
        """Validate tracking number format"""
        # Basic validation - adjust based on your tracking number format
        if not value.startswith('TRK'):
            raise serializers.ValidationError("Invalid tracking number format. Must start with 'TRK'")
        
        if len(value) < 10 or len(value) > 50:
            raise serializers.ValidationError("Tracking number must be between 10 and 50 characters")
        
        # Check if tracking number exists
        from .models import Shipment
        if not Shipment.objects.filter(tracking_number=value).exists():
            raise serializers.ValidationError("Tracking number not found")
        
        return value

class TokenValidationSerializer(serializers.Serializer):
    """
    Serializer for token validation
    """
    token = serializers.CharField(required=True)
    service = serializers.CharField(required=True)
    
    def validate(self, data):
        """Validate token"""
        from rest_framework_simplejwt.tokens import AccessToken
        from rest_framework_simplejwt.exceptions import TokenError
        
        try:
            token = AccessToken(data['token'])
            # Check if token has required claims
            if not token.get('user_id'):
                raise serializers.ValidationError({
                    'token': 'Invalid token format'
                })
            
            # Check if token is intended for this service
            token_service = token.get('service', 'default')
            if token_service != data['service']:
                raise serializers.ValidationError({
                    'token': f'Token not valid for {data["service"]} service'
                })
            
            # Check expiry
            from datetime import datetime
            exp_timestamp = token.get('exp')
            if exp_timestamp and datetime.fromtimestamp(exp_timestamp) < timezone.now():
                raise serializers.ValidationError({
                    'token': 'Token has expired'
                })
            
        except TokenError as e:
            raise serializers.ValidationError({
                'token': str(e)
            })
        
        return data

class ShipmentMetricsSerializer(serializers.Serializer):
    """
    Serializer for shipment metrics
    """
    period = serializers.ChoiceField(
        choices=['day', 'week', 'month', 'quarter', 'year'],
        default='month'
    )
    metrics = serializers.MultipleChoiceField(
        choices=[
            ('total_shipments', 'Total Shipments'),
            ('total_revenue', 'Total Revenue'),
            ('delivery_rate', 'Delivery Rate'),
            ('avg_delivery_time', 'Average Delivery Time'),
            ('status_distribution', 'Status Distribution'),
            ('revenue_trend', 'Revenue Trend'),
            ('top_destinations', 'Top Destinations')
        ],
        required=False
    )
    
    def validate_metrics(self, value):
        """Validate metrics selection"""
        if not value:
            # Default metrics
            value = ['total_shipments', 'total_revenue', 'delivery_rate']
        return value

class ExportSerializer(serializers.Serializer):
    """
    Serializer for data export
    """
    format = serializers.ChoiceField(
        choices=['csv', 'json', 'excel', 'pdf'],
        default='csv'
    )
    data_type = serializers.ChoiceField(
        choices=['shipments', 'tracking_events', 'token_shifts', 'reports'],
        required=True
    )
    filters = serializers.JSONField(required=False, default=dict)
    include_header = serializers.BooleanField(default=True)
    compression = serializers.ChoiceField(
        choices=['none', 'zip', 'gzip'],
        default='none'
    )
    
    def validate_filters(self, value):
        """Validate filter JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Filters must be a JSON object")
        
        # Limit filter size
        import json
        if len(json.dumps(value)) > 5000:
            raise serializers.ValidationError("Filters are too large")
        
        return value