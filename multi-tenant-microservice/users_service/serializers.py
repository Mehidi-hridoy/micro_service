from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import Tenant

User = get_user_model()

class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'domain', 'created_at']

class UserSerializer(serializers.ModelSerializer):
    tenant = TenantSerializer(read_only=True)
    tenant_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 
                 'is_active', 'tenant', 'tenant_id', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
        }
    
    def create(self, validated_data):
        tenant_id = validated_data.pop('tenant_id', None)
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        if tenant_id:
            user.tenant_id = tenant_id
        user.save()
        return user

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom token serializer to include tenant_id"""
    
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        
        # Add custom claims
        token['email'] = user.email
        if user.tenant:
            token['tenant_id'] = user.tenant.id
            token['tenant_name'] = user.tenant.name
        
        return token
    
    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Add tenant info to response
        user = self.user
        if user.tenant:
            data['tenant_id'] = user.tenant.id
            data['tenant_name'] = user.tenant.name
        
        return data
    

    