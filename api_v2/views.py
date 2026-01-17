from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from datetime import timedelta
from users.models import User, UserSession
from shifting.models import Shipment, TrackingEvent, TokenShift
from django.db import models

class UserRegistrationViewV2(generics.CreateAPIView):
    """V2: Enhanced user registration"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        role = request.data.get('role', 'shipper')
        company_name = request.data.get('company_name', '')
        phone = request.data.get('phone', '')
        
        if not all([username, email, password]):
            return Response(
                {'error': 'Username, email, and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            company_name=company_name,
            phone=phone
        )
        
        # Generate tenant ID
        import uuid
        user.tenant_id = f"{company_name.lower().replace(' ', '-')}-{uuid.uuid4().hex[:8]}" if company_name else f"tenant-{uuid.uuid4().hex[:8]}"
        user.save()
        
        refresh = RefreshToken.for_user(user)
        
        # Create user session
        session = UserSession.objects.create(
            user=user,
            session_token=str(refresh.access_token),
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            expires_at=timezone.now() + timedelta(hours=24),
            device_info={'browser': 'Unknown', 'platform': 'Unknown'}
        )
        
        return Response({
            'message': 'User registered successfully with tenant',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'company_name': user.company_name,
                'tenant_id': user.tenant_id
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'session_id': session.id
        }, status=status.HTTP_201_CREATED)
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

class UserLoginViewV2(APIView):
    """V2: Enhanced user login with session tracking"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        
        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = authenticate(username=username, password=password)
        
        if not user:
            return Response(
                {'error': 'Invalid credentials'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        refresh = RefreshToken.for_user(user)
        
        # Create or update user session
        session, created = UserSession.objects.update_or_create(
            user=user,
            session_token=str(refresh.access_token),
            defaults={
                'ip_address': self.get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'expires_at': timezone.now() + timedelta(hours=24),
                'device_info': {'browser': 'Unknown', 'platform': 'Unknown'},
                'is_active': True
            }
        )
        
        user.last_login = timezone.now()
        user.save()
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role,
                'company_name': user.company_name,
                'tenant_id': user.tenant_id
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'session_id': session.id,
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

class UserProfileViewV2(generics.RetrieveAPIView):
    """V2: Get enhanced user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get active sessions
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        # Get shipment stats
        total_shipments = Shipment.objects.filter(tenant=user).count()
        delivered_shipments = Shipment.objects.filter(tenant=user, status='delivered').count()
        
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'company_name': user.company_name,
            'tenant_id': user.tenant_id,
            'phone': user.phone,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
            'stats': {
                'active_sessions': active_sessions,
                'total_shipments': total_shipments,
                'delivered_shipments': delivered_shipments
            }
        })

class UserUpdateViewV2(APIView):
    """V2: Update user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        user = request.user
        
        allowed_fields = ['company_name', 'phone', 'email']
        update_data = {}
        
        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]
        
        if not update_data:
            return Response(
                {'error': 'No valid fields to update'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Update email validation
        if 'email' in update_data and update_data['email'] != user.email:
            if User.objects.filter(email=update_data['email']).exclude(id=user.id).exists():
                return Response(
                    {'error': 'Email already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.save()
        
        return Response({
            'message': 'Profile updated successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'company_name': user.company_name,
                'phone': user.phone
            }
        })

class ChangePasswordViewV2(APIView):
    """V2: Change password"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        user = request.user
        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')
        
        if not old_password or not new_password:
            return Response(
                {'error': 'Old password and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not user.check_password(old_password):
            return Response(
                {'error': 'Old password is incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if old_password == new_password:
            return Response(
                {'error': 'New password cannot be same as old password'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(new_password)
        user.save()
        
        # Invalidate all sessions
        UserSession.objects.filter(user=user, is_active=True).update(
            is_active=False,
            expires_at=timezone.now()
        )
        
        return Response({
            'message': 'Password changed successfully. Please login again.'
        })

class ShipmentListViewV2(generics.ListAPIView):
    """V2: List shipments with filtering"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        shipments = Shipment.objects.filter(tenant=request.user)
        
        # Apply filters
        status_filter = request.query_params.get('status')
        if status_filter:
            shipments = shipments.filter(status=status_filter)
        
        shipment_type_filter = request.query_params.get('shipment_type')
        if shipment_type_filter:
            shipments = shipments.filter(shipment_type=shipment_type_filter)
        
        data = []
        for shipment in shipments:
            data.append({
                'shipment_id': shipment.shipment_id,
                'tracking_number': shipment.tracking_number,
                'shipment_type': shipment.shipment_type,
                'status': shipment.status,
                'description': shipment.description,
                'weight': str(shipment.weight),
                'pickup_address': shipment.pickup_address,
                'delivery_address': shipment.delivery_address,
                'current_location': shipment.current_location,
                'total_amount': str(shipment.total_amount),
                'pickup_date': shipment.pickup_date,
                'estimated_delivery': shipment.estimated_delivery,
                'created_at': shipment.created_at,
                'updated_at': shipment.updated_at
            })
        
        return Response({
            'count': shipments.count(),
            'shipments': data
        })

class ShipmentCreateViewV2(generics.CreateAPIView):
    """V2: Create shipment with more options"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        description = request.data.get('description')
        weight = request.data.get('weight')
        shipment_type = request.data.get('shipment_type', 'parcel')
        pickup_address = request.data.get('pickup_address')
        delivery_address = request.data.get('delivery_address')
        pickup_contact = request.data.get('pickup_contact')
        delivery_contact = request.data.get('delivery_contact')
        shipping_cost = request.data.get('shipping_cost', 50.00)
        tax_amount = request.data.get('tax_amount', 5.00)
        
        if not all([description, weight, pickup_address, delivery_address, pickup_contact, delivery_contact]):
            return Response(
                {'error': 'Required fields: description, weight, pickup_address, delivery_address, pickup_contact, delivery_contact'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            weight = float(weight)
            shipping_cost = float(shipping_cost)
            tax_amount = float(tax_amount)
        except ValueError:
            return Response(
                {'error': 'Weight, shipping_cost, and tax_amount must be numbers'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shipment = Shipment.objects.create(
            tenant=request.user,
            description=description,
            weight=weight,
            shipment_type=shipment_type,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            pickup_contact=pickup_contact,
            delivery_contact=delivery_contact,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount
        )
        
        # Create initial tracking event
        TrackingEvent.objects.create(
            shipment=shipment,
            event_type='CREATED',
            description='Shipment created',
            location=pickup_address,
            remarks='Shipment registered in system'
        )
        
        return Response({
            'message': 'Shipment created successfully',
            'shipment': {
                'shipment_id': shipment.shipment_id,
                'tracking_number': shipment.tracking_number,
                'status': shipment.status,
                'shipment_type': shipment.shipment_type,
                'total_amount': str(shipment.total_amount),
                'tracking_url': f'/api/v2/tracking/{shipment.tracking_number}/'
            }
        }, status=status.HTTP_201_CREATED)

class ShipmentDetailViewV2(generics.RetrieveAPIView):
    """V2: Get detailed shipment info"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            tracking_events = TrackingEvent.objects.filter(shipment=shipment).order_by('event_time')
            events_data = []
            for event in tracking_events:
                events_data.append({
                    'event_type': event.event_type,
                    'description': event.description,
                    'location': event.location,
                    'remarks': event.remarks,
                    'event_time': event.event_time
                })
            
            return Response({
                'shipment': {
                    'shipment_id': shipment.shipment_id,
                    'tracking_number': shipment.tracking_number,
                    'shipment_type': shipment.shipment_type,
                    'status': shipment.status,
                    'description': shipment.description,
                    'weight': str(shipment.weight),
                    'pickup_address': shipment.pickup_address,
                    'delivery_address': shipment.delivery_address,
                    'pickup_contact': shipment.pickup_contact,
                    'delivery_contact': shipment.delivery_contact,
                    'current_location': shipment.current_location,
                    'shipping_cost': str(shipment.shipping_cost),
                    'tax_amount': str(shipment.tax_amount),
                    'total_amount': str(shipment.total_amount),
                    'pickup_date': shipment.pickup_date,
                    'estimated_delivery': shipment.estimated_delivery,
                    'actual_delivery': shipment.actual_delivery,
                    'created_at': shipment.created_at,
                    'updated_at': shipment.updated_at,
                    'notes': shipment.notes
                },
                'tracking_events': events_data,
                'event_count': len(events_data)
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class ShipmentUpdateViewV2(APIView):
    """V2: Update shipment"""
    permission_classes = [permissions.IsAuthenticated]
    
    def patch(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            allowed_fields = [
                'description', 'current_location', 'notes',
                'pickup_date', 'estimated_delivery', 'status'
            ]
            
            update_data = {}
            for field in allowed_fields:
                if field in request.data:
                    update_data[field] = request.data[field]
            
            if not update_data:
                return Response(
                    {'error': 'No valid fields to update'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update status validation
            if 'status' in update_data:
                valid_statuses = ['pending', 'in_transit', 'delivered', 'cancelled']
                if update_data['status'] not in valid_statuses:
                    return Response(
                        {'error': f'Invalid status. Valid options: {valid_statuses}'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                if update_data['status'] == 'delivered' and not shipment.actual_delivery:
                    shipment.actual_delivery = timezone.now()
                    update_data['actual_delivery'] = shipment.actual_delivery
                
                # Create tracking event for status change
                TrackingEvent.objects.create(
                    shipment=shipment,
                    event_type='STATUS_CHANGE',
                    description=f'Status changed from {shipment.status} to {update_data["status"]}',
                    location=shipment.current_location or 'System',
                    remarks=f'Updated by {request.user.username}'
                )
            
            # Update fields
            for field, value in update_data.items():
                setattr(shipment, field, value)
            
            shipment.save()
            
            return Response({
                'message': 'Shipment updated successfully',
                'shipment_id': shipment.shipment_id,
                'updated_fields': list(update_data.keys())
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class ShipmentCancelViewV2(APIView):
    """V2: Cancel shipment with refund calculation"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            if shipment.status == 'cancelled':
                return Response(
                    {'error': 'Shipment is already cancelled'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if shipment.status == 'delivered':
                return Response(
                    {'error': 'Cannot cancel delivered shipment'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Calculate refund based on status
            refund_percentage = 0
            if shipment.status == 'pending':
                refund_percentage = 100
            elif shipment.status == 'in_transit':
                refund_percentage = 50
            
            refund_amount = (shipment.total_amount * refund_percentage) / 100
            
            old_status = shipment.status
            shipment.status = 'cancelled'
            shipment.save()
            
            # Create cancellation event
            TrackingEvent.objects.create(
                shipment=shipment,
                event_type='CANCELLED',
                description=f'Shipment cancelled. Refund: {refund_percentage}%',
                location=shipment.current_location or 'System',
                remarks=f'Changed from {old_status} to cancelled'
            )
            
            return Response({
                'message': 'Shipment cancelled successfully',
                'shipment_id': shipment.shipment_id,
                'new_status': shipment.status,
                'refund_percentage': refund_percentage,
                'refund_amount': str(refund_amount),
                'refund_processed': False  # Placeholder for actual refund
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class TrackingEventListViewV2(generics.ListAPIView):
    """V2: List tracking events for a shipment"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            events = TrackingEvent.objects.filter(shipment=shipment).order_by('event_time')
            data = []
            for event in events:
                data.append({
                    'event_type': event.event_type,
                    'description': event.description,
                    'location': event.location,
                    'remarks': event.remarks,
                    'event_time': event.event_time,
                    'time_ago': self.get_time_ago(event.event_time)
                })
            
            return Response({
                'shipment_id': shipment.shipment_id,
                'tracking_number': shipment.tracking_number,
                'total_events': len(data),
                'events': data
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    def get_time_ago(self, event_time):
        now = timezone.now()
        diff = now - event_time
        
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

class TrackingViewV2(APIView):
    """V2: Enhanced tracking with analytics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, tracking_number):
        try:
            shipment = Shipment.objects.get(
                tracking_number=tracking_number,
                tenant=request.user
            )
            
            events = TrackingEvent.objects.filter(shipment=shipment).order_by('event_time')
            events_data = []
            for event in events:
                events_data.append({
                    'event_type': event.event_type,
                    'description': event.description,
                    'location': event.location,
                    'event_time': event.event_time
                })
            
            # Calculate delivery stats
            is_delayed = False
            time_remaining = None
            
            if shipment.estimated_delivery and shipment.status != 'delivered':
                now = timezone.now()
                if now > shipment.estimated_delivery:
                    is_delayed = True
                else:
                    time_diff = shipment.estimated_delivery - now
                    time_remaining = {
                        'days': time_diff.days,
                        'hours': time_diff.seconds // 3600,
                        'minutes': (time_diff.seconds % 3600) // 60
                    }
            
            return Response({
                'shipment': {
                    'shipment_id': shipment.shipment_id,
                    'tracking_number': shipment.tracking_number,
                    'status': shipment.status,
                    'current_location': shipment.current_location,
                    'pickup_address': shipment.pickup_address,
                    'delivery_address': shipment.delivery_address,
                    'estimated_delivery': shipment.estimated_delivery,
                    'actual_delivery': shipment.actual_delivery
                },
                'tracking_events': events_data,
                'analytics': {
                    'total_events': len(events_data),
                    'is_delayed': is_delayed,
                    'time_remaining': time_remaining,
                    'is_delivered': shipment.status == 'delivered',
                    'delivery_time': shipment.actual_delivery if shipment.status == 'delivered' else None
                }
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class TokenShiftRequestViewV2(APIView):
    """V2: Request token shifting"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        target_service = request.data.get('target_service')
        shift_reason = request.data.get('shift_reason', '')
        
        if not target_service:
            return Response(
                {'error': 'target_service is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        valid_services = ['user-service', 'shipping-service', 'tracking-service', 'analytics-service']
        if target_service not in valid_services:
            return Response(
                {'error': f'Invalid service. Valid options: {valid_services}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, you would generate a new token here
        # For now, we'll simulate token shifting
        import uuid
        simulated_token = f"shifted_token_{uuid.uuid4().hex}"
        
        token_shift = TokenShift.objects.create(
            user=request.user,
            original_token=str(request.auth)[:50] + "...",  # Truncated for security
            shifted_token=simulated_token,
            source_service='api-gateway',
            target_service=target_service,
            shift_reason=shift_reason,
            expires_at=timezone.now() + timedelta(hours=1),
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        return Response({
            'message': 'Token shifted successfully',
            'shift_id': token_shift.id,
            'target_service': target_service,
            'expires_at': token_shift.expires_at,
            'note': 'In production, this would return a real JWT token'
        })
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

class TokenShiftHistoryViewV2(generics.ListAPIView):
    """V2: Get token shifting history"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        shifts = TokenShift.objects.filter(user=request.user).order_by('-shifted_at')
        
        data = []
        for shift in shifts:
            data.append({
                'id': shift.id,
                'source_service': shift.source_service,
                'target_service': shift.target_service,
                'shift_reason': shift.shift_reason,
                'shifted_at': shift.shifted_at,
                'expires_at': shift.expires_at,
                'is_active': shift.is_active,
                'is_expired': shift.is_expired(),
                'usage_count': shift.usage_count,
                'last_used': shift.last_used
            })
        
        return Response({
            'count': len(data),
            'shifts': data
        })

class DashboardStatsViewV2(APIView):
    """V2: Get dashboard statistics"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Shipment stats
        shipments = Shipment.objects.filter(tenant=user)
        total_shipments = shipments.count()
        delivered_shipments = shipments.filter(status='delivered').count()
        pending_shipments = shipments.filter(status='pending').count()
        in_transit_shipments = shipments.filter(status='in_transit').count()
        
        # Revenue stats
        revenue_data = shipments.aggregate(
            total_revenue=models.Sum('total_amount'),
            avg_shipment_value=models.Avg('total_amount')
        )
        
        # Active sessions
        active_sessions = UserSession.objects.filter(
            user=user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).count()
        
        return Response({
            'user': {
                'username': user.username,
                'company_name': user.company_name,
                'tenant_id': user.tenant_id
            },
            'stats': {
                'shipments': {
                    'total': total_shipments,
                    'delivered': delivered_shipments,
                    'pending': pending_shipments,
                    'in_transit': in_transit_shipments,
                    'delivery_rate': (delivered_shipments / total_shipments * 100) if total_shipments > 0 else 0
                },
                'revenue': {
                    'total': str(revenue_data['total_revenue'] or 0),
                    'average_shipment_value': str(revenue_data['avg_shipment_value'] or 0)
                },
                'sessions': {
                    'active': active_sessions
                }
            },
            'timestamp': timezone.now()
        })

class ShipmentReportViewV2(APIView):
    """V2: Generate shipment reports"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Get date range from query params
        days = int(request.query_params.get('days', 30))
        start_date = timezone.now() - timedelta(days=days)
        
        shipments = Shipment.objects.filter(
            tenant=user,
            created_at__gte=start_date
        )
        
        # Status distribution
        status_counts = {}
        for status_choice in Shipment.STATUS_CHOICES:
            status = status_choice[0]
            count = shipments.filter(status=status).count()
            status_counts[status] = count
        
        # Daily trend (last 7 days)
        daily_trend = []
        for i in range(7):
            date = timezone.now() - timedelta(days=i)
            day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            day_end = day_start + timedelta(days=1)
            
            day_shipments = shipments.filter(created_at__range=[day_start, day_end])
            daily_trend.append({
                'date': day_start.date(),
                'shipments': day_shipments.count(),
                'revenue': str(day_shipments.aggregate(total=models.Sum('total_amount'))['total'] or 0)
            })
        
        daily_trend.reverse()  # Oldest to newest
        
        return Response({
            'report_period': {
                'days': days,
                'start_date': start_date.date(),
                'end_date': timezone.now().date()
            },
            'summary': {
                'total_shipments': shipments.count(),
                'status_distribution': status_counts
            },
            'daily_trend': daily_trend,
            'generated_at': timezone.now()
        })
    
