from django.db import connections
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.exceptions import AuthenticationFailed

class TenantMiddleware:
    """
    Middleware to handle multi-tenancy based on JWT token
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        tenant_id = None
        
        # Try to get tenant from JWT token
        try:
            jwt_auth = JWTAuthentication()
            auth_result = jwt_auth.authenticate(request)
            if auth_result:
                user, token = auth_result
                tenant_id = token.payload.get('tenant_id')
        except AuthenticationFailed:
            pass
        
        # Set tenant ID in database connections
        for connection in connections.all():
            connection.tenant_id = tenant_id
        
        request.tenant_id = tenant_id
        
        response = self.get_response(request)
        return response
    
    