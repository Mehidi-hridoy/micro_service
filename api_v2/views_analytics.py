from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import TruncDate, TruncHour
from datetime import datetime, timedelta
from analytics.models import UserAnalytics, ShipmentAnalytics
from shifting.models import Shipment, TrackingEvent

# ========== API VERSION 2 ANALYTICS VIEWS ==========

class DashboardStatsViewV2(APIView):
    """
    Version 2: Get dashboard statistics for current user
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
        
        stats = {
            'user': {
                'id': user.id,
                'username': user.username,
                'role': user.role,
                'tenant_id': user.tenant_id,
                'company_name': user.company_name
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
        
        return Response(stats)
    
    def get_shipment_stats(self, user, start_date, end_date):
        """Get shipment statistics"""
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
        
        return {
            'total_shipments': total,
            'delivered': delivered,
            'in_transit': in_transit,
            'pending': pending,
            'delivery_rate': round(delivery_rate, 2),
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
        
        return {
            'total_activities': total_activities,
            'event_types': list(event_types),
            'last_activity': activities.last().timestamp if activities.exists() else None
        }
    
    def get_revenue_stats(self, user, start_date, end_date):
        """Get revenue statistics"""
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
        
        return {
            'total_revenue': float(revenue_data['total_revenue'] or 0),
            'total_cost': float(revenue_data['total_cost'] or 0),
            'total_tax': float(revenue_data['total_tax'] or 0),
            'net_profit': float((revenue_data['total_revenue'] or 0) - (revenue_data['total_cost'] or 0)),
            'avg_order_value': float((revenue_data['total_revenue'] or 0) / (revenue_data['count'] or 1))
        }

class AnalyticsSummaryViewV2(APIView):
    """
    Version 2: Get comprehensive analytics summary
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
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
                'average_order_value': float(shipment_summary['avg_value'] or 0)
            },
            'user_activity': {
                'total_activities': activity_summary['total_activities'] or 0,
                'unique_event_types': activity_summary['unique_event_types'] or 0
            },
            'performance_metrics': {
                'shipments_per_day': round(shipment_summary['total'] / days, 2) if days > 0 else 0,
                'revenue_per_day': round(float(shipment_summary['revenue'] or 0) / days, 2) if days > 0 else 0,
                'activities_per_day': round(activity_summary['total_activities'] / days, 2) if days > 0 else 0
            }
        }
        
        return Response(summary)

class RealTimeAnalyticsViewV2(APIView):
    """
    Version 2: Get real-time analytics data
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get real-time data (last 1 hour)
        one_hour_ago = timezone.now() - timedelta(hours=1)
        
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
            'active_sessions': 1,  # Placeholder
            'system_health': {
                'status': 'healthy',
                'response_time': 'normal'
            }
        }
        
        return Response(realtime_data)
    
    