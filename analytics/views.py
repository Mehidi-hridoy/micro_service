from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Sum, Avg, F, Q
from django.db.models.functions import TruncDate, TruncMonth, TruncHour
from datetime import datetime, timedelta
from .models import UserAnalytics, ShipmentAnalytics
from .serializers import (
    UserAnalyticsSerializer, ShipmentAnalyticsSerializer,
    AnalyticsSummarySerializer, DashboardStatsSerializer
)
import json

class DashboardStatsView(APIView):
    """
    Get dashboard statistics for current user
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        time_period = request.query_params.get('period', '7d')  # 7d, 30d, 90d
        
        # Calculate date range
        end_date = timezone.now()
        if time_period == '7d':
            start_date = end_date - timedelta(days=7)
        elif time_period == '30d':
            start_date = end_date - timedelta(days=30)
        elif time_period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)
        
        # Get analytics data from database
        # In production, you might use a cache or real-time analytics service
        
        stats = {
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'tenant_id': user.tenant_id
            },
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'period': time_period
            },
            'shipment_stats': self.get_shipment_stats(user, start_date, end_date),
            'user_activity': self.get_user_activity(user, start_date, end_date),
            'revenue_stats': self.get_revenue_stats(user, start_date, end_date),
            'timestamp': timezone.now().isoformat()
        }
        
        serializer = DashboardStatsSerializer(stats)
        return Response(serializer.data)
    
    def get_shipment_stats(self, user, start_date, end_date):
        """Get shipment statistics"""
        from shifting.models import Shipment, TrackingEvent
        
        shipments = Shipment.objects.filter(
            tenant=user,
            created_at__range=[start_date, end_date]
        )
        
        total = shipments.count()
        delivered = shipments.filter(status='delivered').count()
        in_transit = shipments.filter(status='in_transit').count()
        pending = shipments.filter(status='pending').count()
        
        # Calculate delivery rate
        delivery_rate = (delivered / total * 100) if total > 0 else 0
        
        # Average delivery time (in days)
        delivered_shipments = shipments.filter(status='delivered')
        avg_delivery_time = 0
        if delivered_shipments.exists():
            total_time = sum([
                (s.actual_delivery - s.created_at).days 
                for s in delivered_shipments 
                if s.actual_delivery
            ])
            avg_delivery_time = total_time / delivered_shipments.count()
        
        return {
            'total_shipments': total,
            'delivered': delivered,
            'in_transit': in_transit,
            'pending': pending,
            'delivery_rate': round(delivery_time, 2),
            'avg_delivery_time': round(avg_delivery_time, 2),
            'status_distribution': {
                'delivered': delivered,
                'in_transit': in_transit,
                'pending': pending,
                'cancelled': shipments.filter(status='cancelled').count(),
                'delayed': shipments.filter(status='delayed').count()
            }
        }
    
    def get_user_activity(self, user, start_date, end_date):
        """Get user activity analytics"""
        activities = UserAnalytics.objects.filter(
            user=user,
            timestamp__range=[start_date, end_date]
        )
        
        total_activities = activities.count()
        
        # Group by event type
        event_types = activities.values('event_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Hourly distribution
        hourly_dist = activities.annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        return {
            'total_activities': total_activities,
            'event_types': list(event_types),
            'hourly_distribution': list(hourly_dist),
            'last_activity': activities.last().timestamp if activities.exists() else None
        }
    
    def get_revenue_stats(self, user, start_date, end_date):
        """Get revenue statistics"""
        from shifting.models import Shipment
        
        shipments = Shipment.objects.filter(
            tenant=user,
            created_at__range=[start_date, end_date]
        )
        
        revenue_data = shipments.aggregate(
            total_revenue=Sum('total_amount'),
            total_cost=Sum('shipping_cost'),
            total_tax=Sum('tax_amount'),
            count=Count('id')
        )
        
        # Daily revenue trend
        daily_revenue = shipments.annotate(
            date=TruncDate('created_at')
        ).values('date').annotate(
            revenue=Sum('total_amount'),
            shipments=Count('id')
        ).order_by('date')
        
        return {
            'total_revenue': float(revenue_data['total_revenue'] or 0),
            'total_cost': float(revenue_data['total_cost'] or 0),
            'total_tax': float(revenue_data['total_tax'] or 0),
            'net_profit': float((revenue_data['total_revenue'] or 0) - (revenue_data['total_cost'] or 0)),
            'avg_order_value': float((revenue_data['total_revenue'] or 0) / (revenue_data['count'] or 1)),
            'daily_trend': list(daily_revenue)
        }

class UserAnalyticsView(generics.ListCreateAPIView):
    """
    Log and retrieve user analytics
    """
    serializer_class = UserAnalyticsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return UserAnalytics.objects.filter(
            user=self.request.user
        ).order_by('-timestamp')
    
    def create(self, request, *args, **kwargs):
        # Add user and IP info automatically
        data = request.data.copy()
        data['user'] = request.user.id
        data['ip_address'] = self.get_client_ip(request)
        data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')
        
        serializer = self.get_serializer(data=data)
        if serializer.is_valid():
            serializer.save()
            
            # Update aggregated analytics
            self.update_aggregated_analytics(request.user, data)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')
    
    def update_aggregated_analytics(self, user, event_data):
        """Update aggregated analytics in ShipmentAnalytics"""
        try:
            analytics, created = ShipmentAnalytics.objects.get_or_create(
                tenant=user,
                defaults={
                    'total_shipments': 0,
                    'delivered_shipments': 0,
                    'pending_shipments': 0,
                    'total_revenue': 0,
                    'average_delivery_time': 0
                }
            )
            
            # Update based on event type
            event_type = event_data.get('event_type', '')
            
            if event_type == 'SHIPMENT_CREATED':
                analytics.total_shipments += 1
                analytics.pending_shipments += 1
            
            elif event_type == 'SHIPMENT_DELIVERED':
                analytics.delivered_shipments += 1
                analytics.pending_shipments -= 1
            
            elif event_type == 'PAYMENT_RECEIVED':
                amount = event_data.get('event_data', {}).get('amount', 0)
                analytics.total_revenue += float(amount)
            
            analytics.save()
            
        except Exception as e:
            print(f"Error updating aggregated analytics: {e}")

class AnalyticsSummaryView(APIView):
    """
    Get comprehensive analytics summary
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        # Import here to avoid circular imports
        from shifting.models import Shipment, TrackingEvent
        
        # Shipment analytics
        shipments = Shipment.objects.filter(
            tenant=user,
            created_at__gte=start_date
        )
        
        shipment_summary = shipments.aggregate(
            total=Count('id'),
            delivered=Count('id', filter=Q(status='delivered')),
            in_transit=Count('id', filter=Q(status='in_transit')),
            revenue=Sum('total_amount'),
            avg_value=Avg('total_amount')
        )
        
        # User activity analytics
        user_activities = UserAnalytics.objects.filter(
            user=user,
            timestamp__gte=start_date
        )
        
        activity_summary = user_activities.aggregate(
            total_activities=Count('id'),
            unique_event_types=Count('event_type', distinct=True)
        )
        
        # Popular event types
        popular_events = user_activities.values(
            'event_type'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        # Time-based analysis
        hourly_activity = user_activities.annotate(
            hour=TruncHour('timestamp')
        ).values('hour').annotate(
            count=Count('id')
        ).order_by('hour')
        
        # Delivery performance
        delivered_shipments = shipments.filter(status='delivered')
        delivery_times = []
        for shipment in delivered_shipments:
            if shipment.actual_delivery and shipment.created_at:
                delivery_time = (shipment.actual_delivery - shipment.created_at).total_seconds() / 3600  # hours
                delivery_times.append(delivery_time)
        
        avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        summary = {
            'period': {
                'days': days,
                'start_date': start_date.isoformat(),
                'end_date': timezone.now().isoformat()
            },
            'shipments': {
                'total': shipment_summary['total'] or 0,
                'delivered': shipment_summary['delivered'] or 0,
                'in_transit': shipment_summary['in_transit'] or 0,
                'delivery_rate': (
                    (shipment_summary['delivered'] / shipment_summary['total'] * 100) 
                    if shipment_summary['total'] else 0
                ),
                'revenue': float(shipment_summary['revenue'] or 0),
                'average_order_value': float(shipment_summary['avg_value'] or 0),
                'average_delivery_time_hours': round(avg_delivery_time, 2)
            },
            'user_activity': {
                'total_activities': activity_summary['total_activities'] or 0,
                'unique_event_types': activity_summary['unique_event_types'] or 0,
                'popular_events': list(popular_events),
                'hourly_distribution': list(hourly_activity)
            },
            'performance_metrics': {
                'shipments_per_day': round(shipment_summary['total'] / days, 2) if days > 0 else 0,
                'revenue_per_day': round(float(shipment_summary['revenue'] or 0) / days, 2) if days > 0 else 0,
                'activities_per_day': round(activity_summary['total_activities'] / days, 2) if days > 0 else 0
            }
        }
        
        serializer = AnalyticsSummarySerializer(summary)
        return Response(serializer.data)

class RealTimeAnalyticsView(APIView):
    """
    Get real-time analytics data
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get real-time data (last 1 hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
        from shifting.models import Shipment
        
        # Real-time shipment data
        recent_shipments = Shipment.objects.filter(
            tenant=user,
            created_at__gte=one_hour_ago
        )
        
        # Real-time user activity
        recent_activities = UserAnalytics.objects.filter(
            user=user,
            timestamp__gte=one_hour_ago
        )
        
        realtime_data = {
            'timestamp': timezone.now().isoformat(),
            'time_window': '1h',
            'shipments': {
                'created': recent_shipments.count(),
                'updated': Shipment.objects.filter(
                    tenant=user,
                    updated_at__gte=one_hour_ago
                ).count(),
                'status_changes': recent_shipments.exclude(status='pending').count()
            },
            'user_activity': {
                'total_events': recent_activities.count(),
                'event_types': list(recent_activities.values('event_type').annotate(
                    count=Count('id')
                ).order_by('-count'))
            },
            'active_users': 1,  # Placeholder - in multi-user system, count active users
            'system_health': {
                'status': 'healthy',
                'response_time': 'normal',
                'last_check': timezone.now().isoformat()
            }
        }
        
        return Response(realtime_data)