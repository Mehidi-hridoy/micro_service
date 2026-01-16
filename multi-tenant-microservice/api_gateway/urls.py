from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from users_service.views import CustomTokenObtainPairView
from . import views

urlpatterns = [
    # Authentication endpoints
    path('api/token/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # API Version routing
    path('api/v1/', include([
        path('users/', include('users_service.urls_v1')),
        path('shipping/', include('shipping_service.urls_v1')),
    ])),
    
    path('api/v2/', include([
        path('users/', include('users_service.urls_v2')),
        path('shipping/', include('shipping_service.urls_v2')),
    ])),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
]