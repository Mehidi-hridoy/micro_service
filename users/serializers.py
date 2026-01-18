from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from .models import User, UserSession

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2', 
            'first_name', 'last_name', 'role', 'company_name', 'phone'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields don't match."})
        
        # Validate email uniqueness
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError({"email": "A user with this email already exists."})
        
        # Validate username uniqueness
        if User.objects.filter(username=attrs.get('username')).exists():
            raise serializers.ValidationError({"username": "A user with this username already exists."})
        
        return attrs
    
    def create(self, validated_data):
        # Remove password2 from validated_data
        validated_data.pop('password2')
        
        # Set tenant_id based on username
        user = User(**validated_data)
        user.set_password(validated_data['password'])
        
        # Generate tenant_id for shippers/receivers
        if user.role in ['shipper', 'receiver'] and not user.tenant_id:
            user.tenant_id = f"TEN{user.username.upper()}{timezone.now().strftime('%m%d%H%M')}"
        
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)
    device_info = serializers.JSONField(required=False, default=dict)
    
    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')
        
        if not username or not password:
            raise serializers.ValidationError("Both username and password are required.")
        
        return attrs

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'company_name', 'phone', 'tenant_id', 
            'is_verified', 'date_joined', 'last_login'
        ]
        read_only_fields = ['id', 'username', 'date_joined', 'last_login', 'tenant_id']

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'company_name', 'phone'
        ]
    
    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use.")
        return value

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password2 = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password2']:
            raise serializers.ValidationError({"new_password": "Password fields don't match."})
        
        # Check if new password is different from old
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from old password."}
            )
        
        return attrs
    
    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value


class UserSessionSerializer(serializers.ModelSerializer):
    is_expired = serializers.SerializerMethodField()
    
    class Meta:
        model = UserSession
        fields = [
            'id', 'session_token', 'device_info', 'ip_address',
            'user_agent', 'login_at', 'last_activity', 'expires_at',
            'is_active', 'is_expired'
        ]
        read_only_fields = fields
    
    def get_is_expired(self, obj):
        return obj.is_expired()

class UserSessionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSession
        fields = ['device_info', 'ip_address', 'user_agent', 'expires_at']
        read_only_fields = ['ip_address', 'user_agent', 'expires_at']

class RevokeSessionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=200, required=False)
    
    def validate(self, attrs):
        session = self.context.get('session')
        
        if not session.is_active:
            raise serializers.ValidationError({"detail": "Session is already revoked."})
        
        if session.is_expired():
            raise serializers.ValidationError({"detail": "Session is already expired."})
        
        return attrs

# Combined serializers for authentication responses
class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user = UserProfileSerializer()
    session = UserSessionSerializer()

class LogoutResponseSerializer(serializers.Serializer):
    detail = serializers.CharField(default="Successfully logged out")
    session_revoked = serializers.BooleanField()

# Additional serializer for admin user management
class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'company_name', 'is_verified', 'date_joined'
        ]

class AdminUserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['role', 'is_verified', 'company_name', 'phone']
    
    def validate_role(self, value):
        user = self.instance
        
        # Prevent changing role of tenant admin if they're the only admin
        if user.role == 'admin' and value != 'admin':
            # Check if this is the only admin for this tenant
            admin_count = User.objects.filter(
                tenant_id=user.tenant_id, 
                role='admin'
            ).count()
            
            if admin_count <= 1:
                raise serializers.ValidationError(
                    "Cannot change role of the only admin for this tenant."
                )
        
        return value
    

class TenantSerializer(serializers.ModelSerializer):
    """Serializer for tenant operations"""
    
    # Include password fields for creation/updates
    password = serializers.CharField(
        write_only=True, 
        required=False,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True, 
        required=False,
        style={'input_type': 'password'}
    )
    
    # Computed fields
    user_count = serializers.SerializerMethodField()
    active_user_count = serializers.SerializerMethodField()
    created_shipments_count = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'company_name', 'phone',
            'tenant_id', 'role', 'is_verified', 'date_joined',
            'last_login', 'user_count', 'active_user_count',
            'created_shipments_count'
        ]
        read_only_fields = [
            'id', 'tenant_id', 'role', 'date_joined', 
            'last_login', 'user_count', 'active_user_count',
            'created_shipments_count'
        ]
        extra_kwargs = {
            'email': {'required': True},
            'company_name': {'required': True}
        }
    
    def get_user_count(self, obj):
        """Get total number of users under this tenant"""
        if obj.tenant_id:
            return User.objects.filter(tenant_id=obj.tenant_id).count()
        return 0
    
    def get_active_user_count(self, obj):
        """Get number of active users under this tenant"""
        if obj.tenant_id:
            # Assuming active users are those logged in recently (last 30 days)
            thirty_days_ago = timezone.now() - timezone.timedelta(days=30)
            return User.objects.filter(
                tenant_id=obj.tenant_id,
                last_login__gte=thirty_days_ago
            ).count()
        return 0
    
    def get_created_shipments_count(self, obj):
        """Get number of shipments created by this tenant"""
        if obj.tenant_id:
            # You'll need to import Shipment model or adjust this based on your app structure
            try:
                from shipments.models import Shipment
                return Shipment.objects.filter(tenant=obj).count()
            except ImportError:
                return 0
        return 0
    
    def validate(self, attrs):
        """Validate tenant data"""
        # Password validation for creation
        if self.instance is None:  # Creating new tenant
            if 'password' not in attrs or 'password2' not in attrs:
                raise serializers.ValidationError({
                    "password": "Password and confirmation are required for new tenants."
                })
            if attrs['password'] != attrs['password2']:
                raise serializers.ValidationError({
                    "password": "Password fields don't match."
                })
        
        # Password validation for updates
        elif 'password' in attrs or 'password2' in attrs:
            if 'password' not in attrs or 'password2' not in attrs:
                raise serializers.ValidationError({
                    "password": "Both password and confirmation are required to change password."
                })
            if attrs['password'] != attrs['password2']:
                raise serializers.ValidationError({
                    "password": "Password fields don't match."
                })
        
        # Email uniqueness validation
        email = attrs.get('email')
        if email:
            queryset = User.objects.filter(email=email)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    "email": "A user with this email already exists."
                })
        
        # Username uniqueness validation
        username = attrs.get('username')
        if username:
            queryset = User.objects.filter(username=username)
            if self.instance:
                queryset = queryset.exclude(pk=self.instance.pk)
            if queryset.exists():
                raise serializers.ValidationError({
                    "username": "A user with this username already exists."
                })
        
        # Company name validation
        if 'company_name' in attrs and not attrs['company_name'].strip():
            raise serializers.ValidationError({
                "company_name": "Company name cannot be empty."
            })
        
        return attrs
    
    def create(self, validated_data):
        """Create a new tenant (admin user)"""
        # Remove password2 from validated_data
        password2 = validated_data.pop('password2', None)
        password = validated_data.pop('password')
        
        # Create tenant user with admin role
        user = User(**validated_data)
        user.set_password(password)
        user.role = 'admin'
        
        # Generate unique tenant_id
        if not user.tenant_id:
            timestamp = timezone.now().strftime('%Y%m%d%H%M%S')
            username_prefix = user.username[:8].upper()
            user.tenant_id = f"TEN_{username_prefix}_{timestamp}"
        
        user.is_verified = True  # Auto-verify tenant admins
        user.save()
        
        return user
    
    def update(self, instance, validated_data):
        """Update tenant information"""
        # Handle password change
        if 'password' in validated_data:
            password = validated_data.pop('password')
            validated_data.pop('password2', None)  # Remove password2 if present
            instance.set_password(password)
        
        # Update other fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance
    
    def to_representation(self, instance):
        """Custom representation to hide password fields in response"""
        representation = super().to_representation(instance)
        
        # Remove password-related fields from response
        representation.pop('password', None)
        representation.pop('password2', None)
        
        # Add tenant status information
        representation['tenant_status'] = self.get_tenant_status(instance)
        
        return representation
    
    def get_tenant_status(self, instance):
        """Get tenant status information"""
        if not instance.tenant_id:
            return "individual"
        
        user_count = self.get_user_count(instance)
        if user_count == 1:
            return "single_admin"
        elif user_count > 1:
            return "active_tenant"
        else:
            return "inactive"

class TenantCreateSerializer(serializers.ModelSerializer):
    """Serializer specifically for tenant creation (simplified version)"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    
    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password2',
            'first_name', 'last_name', 'company_name', 'phone'
        ]
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields don't match."})
        
        if User.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Email already exists."})
        
        if User.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Username already exists."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        return TenantSerializer().create(validated_data)

class TenantListSerializer(serializers.ModelSerializer):
    """Serializer for listing tenants with summary information"""
    
    user_count = serializers.SerializerMethodField()
    last_activity = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'company_name', 'tenant_id',
            'is_verified', 'date_joined', 'user_count', 'last_activity'
        ]
    
    def get_user_count(self, obj):
        if obj.tenant_id:
            return User.objects.filter(tenant_id=obj.tenant_id).count()
        return 1  # Just the admin user
    
    def get_last_activity(self, obj):
        if obj.tenant_id:
            # Get the latest login time among all tenant users
            latest_user = User.objects.filter(
                tenant_id=obj.tenant_id
            ).order_by('-last_login').first()
            return latest_user.last_login if latest_user and latest_user.last_login else None
        return obj.last_login

class TenantDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed tenant view"""
    
    users = serializers.SerializerMethodField()
    tenant_stats = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'company_name', 'phone', 'tenant_id', 'is_verified',
            'date_joined', 'last_login', 'users', 'tenant_stats'
        ]
    
    def get_users(self, obj):
        """Get all users under this tenant"""
        if obj.tenant_id:
            users = User.objects.filter(tenant_id=obj.tenant_id).exclude(pk=obj.pk)
            return UserProfileSerializer(users, many=True).data
        return []
    
    def get_tenant_stats(self, obj):
        """Get statistics for this tenant"""
        if not obj.tenant_id:
            return None
        
        from django.db.models import Count, Q
        
        # Get user statistics
        users = User.objects.filter(tenant_id=obj.tenant_id)
        total_users = users.count()
        
        # Count users by role
        role_counts = users.values('role').annotate(count=Count('role'))
        
        # Get verified user count
        verified_users = users.filter(is_verified=True).count()
        
        return {
            'total_users': total_users,
            'verified_users': verified_users,
            'role_distribution': list(role_counts),
            'created_at': obj.date_joined.strftime('%Y-%m-%d %H:%M:%S'),
            'tenant_age_days': (timezone.now() - obj.date_joined).days
        }

