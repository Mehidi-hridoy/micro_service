from rest_framework import serializers
from django.utils import timezone
from datetime import datetime, timedelta
from .models import UserAnalytics, ShipmentAnalytics

class UserAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for UserAnalytics model
    """
    user = serializers.StringRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    formatted_timestamp = serializers.SerializerMethodField()
    time_ago = serializers.SerializerMethodField()
    device_info_summary = serializers.SerializerMethodField()
    
    class Meta:
        model = UserAnalytics
        fields = [
            'id', 'user', 'user_id', 'username',
            'event_type', 'event_type_display',
            'event_data', 'ip_address', 'user_agent',
            'timestamp', 'formatted_timestamp', 'time_ago',
            'device_info_summary'
        ]
        read_only_fields = ['id', 'timestamp', 'ip_address', 'user_agent']
    
    def get_formatted_timestamp(self, obj):
        """Return formatted timestamp"""
        return obj.timestamp.strftime('%Y-%m-%d %H:%M:%S') if obj.timestamp else None
    
    def get_time_ago(self, obj):
        """Return human-readable time difference"""
        if not obj.timestamp:
            return None
        
        now = timezone.now()
        diff = now - obj.timestamp
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
        else:
            return "Just now"
    
    def get_device_info_summary(self, obj):
        """Extract device information from user_agent"""
        user_agent = obj.user_agent or ''
        
        # Simple user agent parsing
        device_info = {
            'browser': 'Unknown',
            'platform': 'Unknown',
            'is_mobile': False,
            'is_bot': False
        }
        
        # Browser detection
        browsers = [
            ('Chrome', 'Chrome'),
            ('Firefox', 'Firefox'),
            ('Safari', 'Safari'),
            ('Edge', 'Edge'),
            ('Opera', 'Opera'),
            ('IE', 'Internet Explorer')
        ]
        
        for keyword, browser_name in browsers:
            if keyword in user_agent:
                device_info['browser'] = browser_name
                break
        
        # Platform detection
        platforms = [
            ('Windows', 'Windows'),
            ('Mac', 'macOS'),
            ('Linux', 'Linux'),
            ('Android', 'Android'),
            ('iPhone', 'iOS'),
            ('iPad', 'iOS')
        ]
        
        for keyword, platform_name in platforms:
            if keyword in user_agent:
                device_info['platform'] = platform_name
                break
        
        # Mobile detection
        mobile_keywords = ['Mobile', 'Android', 'iPhone', 'iPad']
        device_info['is_mobile'] = any(keyword in user_agent for keyword in mobile_keywords)
        
        # Bot detection
        bot_keywords = ['bot', 'crawler', 'spider', 'Bot']
        device_info['is_bot'] = any(keyword.lower() in user_agent.lower() for keyword in bot_keywords)
        
        return device_info
    
    def validate_event_data(self, value):
        """Validate event_data is valid JSON"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("event_data must be a JSON object")
        
        # Limit size of event_data
        import json
        if len(json.dumps(value)) > 5000:  # 5KB limit
            raise serializers.ValidationError("event_data is too large (max 5KB)")
        
        return value
    
    def validate_event_type(self, value):
        """Validate event_type"""
        # List of allowed event types
        allowed_events = [
            'LOGIN', 'LOGOUT', 'REGISTER', 'PASSWORD_CHANGE',
            'PROFILE_UPDATE', 'SHIPMENT_CREATED', 'SHIPMENT_UPDATED',
            'SHIPMENT_DELETED', 'TRACKING_VIEWED', 'PAYMENT_INITIATED',
            'PAYMENT_COMPLETED', 'TOKEN_SHIFTED', 'SESSION_STARTED',
            'SESSION_ENDED', 'API_CALL', 'ERROR_OCCURRED', 'SEARCH_PERFORMED',
            'REPORT_GENERATED', 'SETTINGS_CHANGED', 'NOTIFICATION_RECEIVED',
            'NOTIFICATION_READ', 'PAGE_VIEW', 'BUTTON_CLICK', 'FORM_SUBMIT',
            'FILE_UPLOAD', 'EXPORT_DATA', 'IMPORT_DATA'
        ]
        
        if value not in allowed_events:
            raise serializers.ValidationError(f"Invalid event type. Allowed types: {', '.join(allowed_events)}")
        
        return value

class ShipmentAnalyticsSerializer(serializers.ModelSerializer):
    """
    Serializer for ShipmentAnalytics model
    """
    tenant = serializers.StringRelatedField(read_only=True)
    tenant_id = serializers.IntegerField(source='tenant.id', read_only=True)
    company_name = serializers.CharField(source='tenant.company_name', read_only=True)
    
    # Calculated fields
    delivery_rate = serializers.SerializerMethodField()
    revenue_per_shipment = serializers.SerializerMethodField()
    pending_rate = serializers.SerializerMethodField()
    growth_rate = serializers.SerializerMethodField()
    formatted_created_at = serializers.SerializerMethodField()
    formatted_updated_at = serializers.SerializerMethodField()
    
    class Meta:
        model = ShipmentAnalytics
        fields = [
            'id', 'tenant', 'tenant_id', 'company_name',
            'total_shipments', 'delivered_shipments', 'pending_shipments',
            'total_revenue', 'average_delivery_time',
            'delivery_rate', 'revenue_per_shipment', 'pending_rate',
            'growth_rate', 'created_at', 'updated_at',
            'formatted_created_at', 'formatted_updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_delivery_rate(self, obj):
        """Calculate delivery success rate"""
        if obj.total_shipments > 0:
            return round((obj.delivered_shipments / obj.total_shipments) * 100, 2)
        return 0.0
    
    def get_revenue_per_shipment(self, obj):
        """Calculate average revenue per shipment"""
        if obj.total_shipments > 0:
            return round(obj.total_revenue / obj.total_shipments, 2)
        return 0.0
    
    def get_pending_rate(self, obj):
        """Calculate pending shipment rate"""
        if obj.total_shipments > 0:
            return round((obj.pending_shipments / obj.total_shipments) * 100, 2)
        return 0.0
    
    def get_growth_rate(self, obj):
        """Calculate growth rate (placeholder - would require historical data)"""
        # This is a simplified calculation
        # In production, you would compare with previous period
        return 0.0
    
    def get_formatted_created_at(self, obj):
        return obj.created_at.strftime('%Y-%m-%d %H:%M:%S') if obj.created_at else None
    
    def get_formatted_updated_at(self, obj):
        return obj.updated_at.strftime('%Y-%m-%d %H:%M:%S') if obj.updated_at else None
    
    def validate(self, data):
        """Custom validation"""
        # Ensure delivered + pending doesn't exceed total
        if 'delivered_shipments' in data and 'pending_shipments' in data and 'total_shipments' in data:
            if data['delivered_shipments'] + data['pending_shipments'] > data['total_shipments']:
                raise serializers.ValidationError(
                    "delivered_shipments + pending_shipments cannot exceed total_shipments"
                )
        
        # Ensure average_delivery_time is positive
        if 'average_delivery_time' in data and data['average_delivery_time'] < 0:
            raise serializers.ValidationError(
                "average_delivery_time must be positive"
            )
        
        # Ensure total_revenue is positive
        if 'total_revenue' in data and data['total_revenue'] < 0:
            raise serializers.ValidationError(
                "total_revenue must be positive"
            )
        
        return data

class AnalyticsEventSerializer(serializers.Serializer):
    """
    Serializer for creating analytics events
    """
    event_type = serializers.CharField(max_length=100, required=True)
    event_data = serializers.JSONField(required=False, default=dict)
    session_id = serializers.CharField(max_length=100, required=False)
    page_url = serializers.URLField(required=False)
    referrer = serializers.URLField(required=False)
    screen_resolution = serializers.CharField(max_length=20, required=False)
    language = serializers.CharField(max_length=10, required=False)
    
    def validate_event_type(self, value):
        """Validate event type"""
        value = value.upper().replace(' ', '_')
        
        # Common event types
        common_events = [
            'PAGE_VIEW', 'BUTTON_CLICK', 'FORM_SUBMIT', 'LOGIN',
            'LOGOUT', 'SEARCH', 'FILTER_APPLIED', 'SORT_APPLIED',
            'ITEM_VIEWED', 'ITEM_ADDED', 'ITEM_REMOVED', 'CHECKOUT_STARTED',
            'PAYMENT_COMPLETED', 'ERROR_OCCURRED', 'SESSION_STARTED',
            'SESSION_EXPIRED', 'NOTIFICATION_RECEIVED', 'SETTINGS_CHANGED'
        ]
        
        # Allow custom events but validate format
        if not value.replace('_', '').isalnum():
            raise serializers.ValidationError("Event type must contain only letters, numbers and underscores")
        
        return value
    
    def validate_event_data(self, value):
        """Validate event_data structure"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("event_data must be a JSON object")
        
        # Limit size
        import json
        if len(json.dumps(value)) > 10000:  # 10KB limit
            raise serializers.ValidationError("event_data is too large (max 10KB)")
        
        # Remove any sensitive data
        sensitive_keys = ['password', 'token', 'secret', 'credit_card', 'ssn']
        for key in list(value.keys()):
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                del value[key]
        
        return value

class AnalyticsSummarySerializer(serializers.Serializer):
    """
    Serializer for analytics summary data
    """
    period = serializers.DictField()
    shipments = serializers.DictField()
    user_activity = serializers.DictField()
    performance_metrics = serializers.DictField()
    generated_at = serializers.DateTimeField(default=timezone.now)

class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for dashboard statistics
    """
    user = serializers.DictField()
    period = serializers.DictField()
    shipment_stats = serializers.DictField()
    user_activity = serializers.DictField()
    revenue_stats = serializers.DictField()
    timestamp = serializers.DateTimeField()

class TimeSeriesDataSerializer(serializers.Serializer):
    """
    Serializer for time series data
    """
    timestamp = serializers.DateTimeField()
    value = serializers.FloatField()
    label = serializers.CharField(required=False)

class AnalyticsFilterSerializer(serializers.Serializer):
    """
    Serializer for analytics filters
    """
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    time_period = serializers.ChoiceField(
        choices=[
            ('today', 'Today'),
            ('yesterday', 'Yesterday'),
            ('7d', 'Last 7 days'),
            ('30d', 'Last 30 days'),
            ('90d', 'Last 90 days'),
            ('month', 'This month'),
            ('last_month', 'Last month'),
            ('year', 'This year'),
            ('custom', 'Custom')
        ],
        default='30d'
    )
    event_type = serializers.CharField(required=False)
    user_id = serializers.IntegerField(required=False)
    tenant_id = serializers.CharField(required=False)
    group_by = serializers.ChoiceField(
        choices=[
            ('hour', 'Hour'),
            ('day', 'Day'),
            ('week', 'Week'),
            ('month', 'Month'),
            ('year', 'Year')
        ],
        default='day'
    )
    limit = serializers.IntegerField(min_value=1, max_value=1000, default=100)
    offset = serializers.IntegerField(min_value=0, default=0)
    
    def validate(self, data):
        """Validate date ranges"""
        if data.get('start_date') and data.get('end_date'):
            if data['start_date'] > data['end_date']:
                raise serializers.ValidationError("start_date cannot be after end_date")
            
            # Limit range to 365 days
            delta = data['end_date'] - data['start_date']
            if delta.days > 365:
                raise serializers.ValidationError("Date range cannot exceed 365 days")
        
        return data

class TopItemsSerializer(serializers.Serializer):
    """
    Serializer for top items analytics
    """
    item_id = serializers.CharField()
    item_name = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()
    revenue = serializers.FloatField(required=False)

class UserBehaviorSerializer(serializers.Serializer):
    """
    Serializer for user behavior analytics
    """
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    total_sessions = serializers.IntegerField()
    total_events = serializers.IntegerField()
    avg_session_duration = serializers.FloatField()
    favorite_event = serializers.CharField()
    last_active = serializers.DateTimeField()

class ConversionRateSerializer(serializers.Serializer):
    """
    Serializer for conversion rate analytics
    """
    step = serializers.CharField()
    visitors = serializers.IntegerField()
    conversions = serializers.IntegerField()
    conversion_rate = serializers.FloatField()
    drop_off_rate = serializers.FloatField()

class GeoAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for geographic analytics
    """
    country = serializers.CharField()
    region = serializers.CharField(required=False)
    city = serializers.CharField(required=False)
    count = serializers.IntegerField()
    percentage = serializers.FloatField()

class DeviceAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for device analytics
    """
    device_type = serializers.CharField()
    browser = serializers.CharField()
    platform = serializers.CharField()
    count = serializers.IntegerField()
    percentage = serializers.FloatField()

class RevenueAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for revenue analytics
    """
    period = serializers.CharField()
    revenue = serializers.FloatField()
    cost = serializers.FloatField()
    profit = serializers.FloatField()
    margin = serializers.FloatField()
    growth = serializers.FloatField(required=False)

class PerformanceMetricSerializer(serializers.Serializer):
    """
    Serializer for performance metrics
    """
    metric_name = serializers.CharField()
    current_value = serializers.FloatField()
    previous_value = serializers.FloatField(required=False)
    change = serializers.FloatField(required=False)
    change_percentage = serializers.FloatField(required=False)
    target_value = serializers.FloatField(required=False)
    status = serializers.ChoiceField(
        choices=['good', 'warning', 'critical', 'neutral'],
        required=False
    )

class RealTimeAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for real-time analytics
    """
    timestamp = serializers.DateTimeField()
    time_window = serializers.CharField()
    shipments = serializers.DictField()
    user_activity = serializers.DictField()
    active_users = serializers.IntegerField()
    system_health = serializers.DictField()

class ExportAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for analytics export
    """
    format = serializers.ChoiceField(choices=['csv', 'json', 'excel', 'pdf'])
    data_type = serializers.ChoiceField(
        choices=['user_analytics', 'shipment_analytics', 'summary', 'custom']
    )
    filters = AnalyticsFilterSerializer(required=False)
    include_charts = serializers.BooleanField(default=False)
    compression = serializers.ChoiceField(
        choices=['none', 'zip', 'gzip'],
        default='none'
    )

class AnalyticsAlertSerializer(serializers.Serializer):
    """
    Serializer for analytics alerts
    """
    alert_type = serializers.ChoiceField(
        choices=['threshold', 'anomaly', 'trend', 'predictive']
    )
    metric = serializers.CharField()
    condition = serializers.CharField()
    value = serializers.FloatField()
    severity = serializers.ChoiceField(
        choices=['low', 'medium', 'high', 'critical']
    )
    message = serializers.CharField()
    triggered_at = serializers.DateTimeField(default=timezone.now)
    is_resolved = serializers.BooleanField(default=False)

class PredictiveAnalyticsSerializer(serializers.Serializer):
    """
    Serializer for predictive analytics
    """
    prediction_type = serializers.ChoiceField(
        choices=['demand', 'revenue', 'conversion', 'churn']
    )
    horizon = serializers.ChoiceField(
        choices=['1d', '7d', '30d', '90d', '1y']
    )
    confidence_level = serializers.FloatField(min_value=0, max_value=1)
    predictions = serializers.ListField(child=TimeSeriesDataSerializer())
    factors = serializers.ListField(child=serializers.DictField())

class CohortAnalysisSerializer(serializers.Serializer):
    """
    Serializer for cohort analysis
    """
    cohort_period = serializers.CharField()
    cohort_size = serializers.IntegerField()
    retention_data = serializers.ListField(child=serializers.DictField())
    average_retention = serializers.FloatField()
    lifetime_value = serializers.FloatField()

class FunnelAnalysisSerializer(serializers.Serializer):
    """
    Serializer for funnel analysis
    """
    funnel_name = serializers.CharField()
    steps = serializers.ListField(child=serializers.DictField())
    total_conversion = serializers.FloatField()
    average_time_to_convert = serializers.FloatField()
    bottlenecks = serializers.ListField(child=serializers.CharField())

class A_BTestResultSerializer(serializers.Serializer):
    """
    Serializer for A/B test results
    """
    test_name = serializers.CharField()
    variant_a = serializers.DictField()
    variant_b = serializers.DictField()
    confidence_level = serializers.FloatField()
    is_significant = serializers.BooleanField()
    recommendation = serializers.CharField()
    test_duration = serializers.DurationField()

    