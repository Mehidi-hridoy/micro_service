from rest_framework import generics, permissions, status, filters
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from users.models import User, UserSession
from users.serializers import (
    UserRegistrationSerializer, UserLoginSerializer,
    UserProfileSerializer, ChangePasswordSerializer,
    UserUpdateSerializer, UserSessionSerializer
)

# ========== API VERSION 2 AUTH VIEWS ==========

class UserRegistrationViewV2(generics.CreateAPIView):
    """
    Version 2: Enhanced user registration with tenant creation
    """
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Add custom claims
            access_token['user_id'] = user.id
            access_token['username'] = user.username
            access_token['role'] = user.role
            access_token['tenant_id'] = user.tenant_id
            
            # Create user session
            session = UserSession.objects.create(
                user=user,
                session_token=str(access_token),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                expires_at=timezone.now() + timezone.timedelta(hours=24),
                device_info=self.get_device_info(request)
            )
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(access_token),
                'session_id': session.id,
                'message': 'User registered successfully with tenant'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    def get_device_info(self, request):
        return {
            'browser': request.META.get('HTTP_USER_AGENT', 'Unknown'),
            'platform': request.META.get('HTTP_SEC_CH_UA_PLATFORM', 'Unknown'),
            'mobile': request.META.get('HTTP_SEC_CH_UA_MOBILE', '?0') == '?1'
        }

class UserLoginViewV2(APIView):
    """
    Version 2: Enhanced user login with session tracking
    """
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        
        if serializer.is_valid():
            user = serializer.validated_data['user']
            
            # Generate tokens
            refresh = RefreshToken.for_user(user)
            access_token = refresh.access_token
            
            # Add custom claims
            access_token['user_id'] = user.id
            access_token['username'] = user.username
            access_token['role'] = user.role
            access_token['tenant_id'] = user.tenant_id
            
            # Create or update user session
            session, created = UserSession.objects.update_or_create(
                user=user,
                session_token=str(access_token),
                defaults={
                    'ip_address': self.get_client_ip(request),
                    'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                    'expires_at': timezone.now() + timezone.timedelta(hours=24),
                    'device_info': self.get_device_info(request),
                    'is_active': True
                }
            )
            
            # Update last login
            user.last_login = timezone.now()
            user.save()
            
            return Response({
                'user': UserProfileSerializer(user).data,
                'refresh': str(refresh),
                'access': str(access_token),
                'session_id': session.id,
                'expires_in': 3600,
                'token_type': 'Bearer',
                'message': 'Login successful'
            })
        
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        return x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
    
    def get_device_info(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
        return {
            'browser': self._parse_browser(user_agent),
            'platform': self._parse_platform(user_agent),
            'is_mobile': 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent
        }
    
    def _parse_browser(self, user_agent):
        browsers = ['Chrome', 'Firefox', 'Safari', 'Edge', 'Opera']
        for browser in browsers:
            if browser in user_agent:
                return browser
        return 'Unknown'
    
    def _parse_platform(self, user_agent):
        platforms = ['Windows', 'Mac', 'Linux', 'Android', 'iPhone']
        for platform in platforms:
            if platform in user_agent:
                return platform
        return 'Unknown'

class UserLogoutViewV2(APIView):
    """
    Version 2: Enhanced logout with session management
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Deactivate current session
            UserSession.objects.filter(
                user=request.user,
                session_token=str(request.auth)
            ).update(is_active=False, expires_at=timezone.now())
            
            return Response({
                "message": "Logged out successfully",
                "timestamp": timezone.now().isoformat()
            }, status=status.HTTP_205_RESET_CONTENT)
            
        except Exception as e:
            return Response({
                "error": "Invalid token",
                "details": str(e)
            }, status=status.HTTP_400_BAD_REQUEST)

class UserProfileViewV2(generics.RetrieveAPIView):
    """
    Version 2: Get user profile with enhanced data
    """
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class UserUpdateViewV2(generics.UpdateAPIView):
    """
    Version 2: Update user profile
    """
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        if serializer.is_valid():
            # Save the update
            self.perform_update(serializer)
            
            # Return updated data
            return Response({
                'message': 'Profile updated successfully',
                'user': UserProfileSerializer(instance).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordViewV2(APIView):
    """
    Version 2: Change password with security features
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            
            # Verify old password
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({
                    "error": "Old password is incorrect"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Set new password
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Invalidate all active sessions
            UserSession.objects.filter(user=user, is_active=True).update(
                is_active=False,
                expires_at=timezone.now()
            )
            
            # Generate new tokens
            refresh = RefreshToken.for_user(user)
            
            return Response({
                "message": "Password updated successfully. Please login again.",
                "refresh": str(refresh),
                "access": str(refresh.access_token)
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserSessionListViewV2(generics.ListAPIView):
    """
    Version 2: List all active sessions for the current user
    """
    serializer_class = UserSessionSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering_fields = ['login_at', 'last_activity']
    
    def get_queryset(self):
        return UserSession.objects.filter(
            user=self.request.user,
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-last_activity')
    
    