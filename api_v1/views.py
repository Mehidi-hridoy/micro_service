from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from users.models import User
from shifting.models import Shipment, TrackingEvent

class UserRegistrationViewV1(generics.CreateAPIView):
    """V1: Basic user registration"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Simplified registration for v1
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        
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
            password=password
        )
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'message': 'User registered successfully',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)

class UserLoginViewV1(APIView):
    """V1: Basic user login"""
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
        
        return Response({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'role': user.role
            },
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        })

class UserProfileViewV1(generics.RetrieveAPIView):
    """V1: Get user profile"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'company_name': user.company_name,
            'phone': user.phone,
            'date_joined': user.date_joined
        })

class ShipmentListViewV1(generics.ListCreateAPIView):
    """V1: List and create shipments"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return Shipment.objects.filter(tenant=self.request.user)
    
    def list(self, request, *args, **kwargs):
        shipments = self.get_queryset()
        data = []
        for shipment in shipments:
            data.append({
                'shipment_id': shipment.shipment_id,
                'tracking_number': shipment.tracking_number,
                'status': shipment.status,
                'description': shipment.description,
                'pickup_address': shipment.pickup_address,
                'delivery_address': shipment.delivery_address,
                'total_amount': str(shipment.total_amount),
                'created_at': shipment.created_at
            })
        return Response({'shipments': data})
    
    def create(self, request, *args, **kwargs):
        # Simplified shipment creation for v1
        description = request.data.get('description')
        weight = request.data.get('weight')
        pickup_address = request.data.get('pickup_address')
        delivery_address = request.data.get('delivery_address')
        pickup_contact = request.data.get('pickup_contact')
        delivery_contact = request.data.get('delivery_contact')
        
        if not all([description, weight, pickup_address, delivery_address, pickup_contact, delivery_contact]):
            return Response(
                {'error': 'All fields are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        shipment = Shipment.objects.create(
            tenant=request.user,
            description=description,
            weight=weight,
            pickup_address=pickup_address,
            delivery_address=delivery_address,
            pickup_contact=pickup_contact,
            delivery_contact=delivery_contact,
            shipping_cost=50.00,  # Default cost for v1
            tax_amount=5.00
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
                'status': shipment.status
            }
        }, status=status.HTTP_201_CREATED)

class ShipmentCreateViewV1(generics.CreateAPIView):
    """V1: Create shipment (alternative endpoint)"""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        return ShipmentListViewV1().create(request, *args, **kwargs)

class ShipmentDetailViewV1(generics.RetrieveAPIView):
    """V1: Get shipment details"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, shipment_id):
        try:
            shipment = Shipment.objects.get(
                shipment_id=shipment_id,
                tenant=request.user
            )
            
            tracking_events = TrackingEvent.objects.filter(shipment=shipment)
            events_data = []
            for event in tracking_events:
                events_data.append({
                    'event_type': event.event_type,
                    'description': event.description,
                    'location': event.location,
                    'event_time': event.event_time
                })
            
            return Response({
                'shipment': {
                    'shipment_id': shipment.shipment_id,
                    'tracking_number': shipment.tracking_number,
                    'status': shipment.status,
                    'description': shipment.description,
                    'weight': str(shipment.weight),
                    'pickup_address': shipment.pickup_address,
                    'delivery_address': shipment.delivery_address,
                    'pickup_contact': shipment.pickup_contact,
                    'delivery_contact': shipment.delivery_contact,
                    'current_location': shipment.current_location,
                    'total_amount': str(shipment.total_amount),
                    'created_at': shipment.created_at,
                    'estimated_delivery': shipment.estimated_delivery
                },
                'tracking_events': events_data
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class ShipmentCancelViewV1(APIView):
    """V1: Cancel a shipment"""
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
            
            shipment.status = 'cancelled'
            shipment.save()
            
            # Create cancellation event
            TrackingEvent.objects.create(
                shipment=shipment,
                event_type='CANCELLED',
                description='Shipment cancelled',
                location=shipment.current_location or 'System',
                remarks='Cancelled by user'
            )
            
            return Response({
                'message': 'Shipment cancelled successfully',
                'shipment_id': shipment.shipment_id,
                'new_status': shipment.status
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )

class TrackingViewV1(APIView):
    """V1: Track shipment by tracking number"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request, tracking_number):
        try:
            shipment = Shipment.objects.get(
                tracking_number=tracking_number,
                tenant=request.user
            )
            
            tracking_events = TrackingEvent.objects.filter(shipment=shipment).order_by('event_time')
            events_data = []
            for event in tracking_events:
                events_data.append({
                    'event_type': event.event_type,
                    'description': event.description,
                    'location': event.location,
                    'event_time': event.event_time
                })
            
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
                'tracking_history': events_data
            })
            
        except Shipment.DoesNotExist:
            return Response(
                {'error': 'Shipment not found'},
                status=status.HTTP_404_NOT_FOUND
            )