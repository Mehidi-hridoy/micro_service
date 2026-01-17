from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils import timezone
from datetime import timedelta
import jwt
from shifting.models import TokenShift
from shifting.serializers import TokenShiftSerializer, TokenShiftRequestSerializer

# ========== API VERSION 2 TOKEN SHIFTING VIEWS ==========

class TokenShiftRequestViewV2(APIView):
    """
    Version 2: Request token shifting to another service
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = TokenShiftRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            user = request.user
            target_service = serializer.validated_data['target_service']
            shift_reason = serializer.validated_data.get('shift_reason', '')
            expires_in = serializer.validated_data.get('expires_in', 3600)
            
            # Generate new token for target service
            refresh = RefreshToken.for_user(user)
            new_token = str(refresh.access_token)
            
            # Add custom claims for target service
            try:
                decoded_token = jwt.decode(
                    new_token, 
                    options={"verify_signature": False}
                )
                decoded_token['service'] = target_service
                decoded_token['shifted_at'] = timezone.now().isoformat()
                
                # In production, you would re-sign with your secret
                # For now, we'll store the original token
            except:
                pass
            
            # Create token shift record
            token_shift = TokenShift.objects.create(
                user=user,
                original_token=str(request.auth),  # Current token
                shifted_token=new_token,
                source_service='api-gateway',
                target_service=target_service,
                shift_reason=shift_reason,
                token_type='access',
                expires_at=timezone.now() + timedelta(seconds=expires_in),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'shift_id': token_shift.id,
                'new_token': new_token,
                'target_service': target_service,
                'expires_at': token_shift.expires_at.isoformat(),
                'expires_in': expires_in,
                'message': 'Token shifted successfully'
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def get_client_ip(self, request):
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        return xff.split(',')[0] if xff else request.META.get('REMOTE_ADDR')

class TokenShiftHistoryViewV2(generics.ListAPIView):
    """
    Version 2: Get token shifting history for current user
    """
    serializer_class = TokenShiftSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        return TokenShift.objects.filter(
            user=self.request.user
        ).order_by('-shifted_at')

class RevokeTokenShiftViewV2(APIView):
    """
    Version 2: Revoke a shifted token
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, shift_id):
        try:
            token_shift = TokenShift.objects.get(
                id=shift_id,
                user=request.user,
                is_active=True
            )
            
            token_shift.is_active = False
            token_shift.save()
            
            return Response({
                'message': 'Shifted token revoked successfully',
                'shift_id': shift_id,
                'token_preview': f"{token_shift.shifted_token[:10]}...{token_shift.shifted_token[-10:]}"
            })
            
        except TokenShift.DoesNotExist:
            return Response({
                'error': 'Token shift record not found or already revoked'
            }, status=status.HTTP_404_NOT_FOUND)
        
        