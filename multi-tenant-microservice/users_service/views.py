from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from django.db import connection
from .models import Tenant
from .serializers import (
    UserSerializer, TenantSerializer, 
    CustomTokenObtainPairSerializer
)

User = get_user_model()

class TenantViewSet(viewsets.ModelViewSet):
    """API endpoint for managing tenants"""
    queryset = Tenant.objects.all()
    serializer_class = TenantSerializer
    permission_classes = [permissions.IsAdminUser]

class UserViewSet(viewsets.ModelViewSet):
    """API endpoint for managing users"""
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter users by tenant"""
        queryset = super().get_queryset()
        
        # If user is not admin, only show users from same tenant
        if not self.request.user.is_staff:
            queryset = queryset.filter(tenant=self.request.user.tenant)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """Get current user info"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def register(self, request):
        """User registration"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Set tenant for new user
        tenant_id = request.data.get('tenant_id')
        if not tenant_id and request.user.tenant:
            tenant_id = request.user.tenant.id
        
        user = serializer.save(tenant_id=tenant_id)
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)

class CustomTokenObtainPairView(TokenObtainPairView):
    """Custom token obtain view with tenant support"""
    serializer_class = CustomTokenObtainPairSerializer

    