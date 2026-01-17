from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator
from .models import User, UserSession
import uuid

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    email = serializers.EmailField(
        required=True,
        validators=[EmailValidator()]
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'phone', 
            'company_name', 'role', 'tenant_id'
        ]
        extra_kwargs = {
            'username': {'required': True},
            'email': {'required': True},
        }
    
    def validate(self, attrs):
        # Check password match
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({
                "password": "Password fields didn't match."
            })
        
        # Check if username exists
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({
                "username": "Username already exists."
            })
        
        # Check if email exists
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({
                "email": "Email already exists."
            })
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        
        # Generate tenant_id if not provided
        if not validated_data.get('tenant_id'):
            company_part = validated_data.get('company_name', 'company').replace(' ', '-').lower()
            unique_part = str(uuid.uuid4())[:8]
            validated_data['tenant_id'] = f"{company_part}-{unique_part}"
        
        # Create user
        user = User.objects.create_user(**validated_data)
        
        # Set additional fields
        user.is_active = True
        user.is_verified = True
        user.save()
        
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        write_only=True, 
        required=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError("Both username and password are required.")
        
        user = authenticate(username=username, password=password)
        
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        
        if not user.is_active:
            raise serializers.ValidationError("Account is disabled. Please contact administrator.")
        
        attrs['user'] = user
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'full_name',
            'phone', 'company_name', 'role', 'tenant_id', 
            'is_verified', 'is_active', 'date_joined', 'last_login',
            'profile_picture'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']
    
    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'company_name', 'profile_picture'
        ]
    
    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("Email already exists.")
        return value

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    confirm_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({
                "new_password": "New password and confirmation don't match."
            })
        
        # Check if new password is same as old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                "new_password": "New password cannot be same as old password."
            })
        
        return attrs

class TenantSerializer(serializers.ModelSerializer):
    total_users = serializers.SerializerMethodField()
    active_shipments = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'company_name', 'tenant_id',
            'role', 'phone', 'date_joined', 'last_login',
            'is_active', 'is_verified', 'total_users', 'active_shipments'
        ]
    
    def get_total_users(self, obj):
        # This would typically come from another service or cache
        return User.objects.filter(tenant_id=obj.tenant_id).count()
    
    def get_active_shipments(self, obj):
        # This would typically come from shipping service
        return 0  # Placeholder

class UserSessionSerializer(serializers.ModelSerializer):
    browser = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'device_info', 'ip_address', 'user_agent',
            'login_at', 'last_activity', 'expires_at', 'is_active',
            'browser', 'location'
        ]
    
    def get_browser(self, obj):
        device_info = obj.device_info or {}
        return device_info.get('browser', 'Unknown')
    
    def get_location(self, obj):
        # In production, you would use IP geolocation service
        return "Unknown"
    
    