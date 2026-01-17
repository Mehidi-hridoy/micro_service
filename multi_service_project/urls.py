from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

# Swagger/OpenAPI configuration
schema_view = get_schema_view(
    openapi.Info(
        title="Shipping Management Microservices API",
        default_version='v1',
        description="Multi-tenant shipping management system with token shifting",
        terms_of_service="https://www.example.com/terms/",
        contact=openapi.Contact(email="contact@example.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),
    
    # API Documentation
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
    
    # API Version 1 (Basic Features)
    path('api/v1/', include([
        path('auth/', include('api_v1.urls')),
        path('shipments/', include('api_v1.urls_shipments')),
        path('tracking/', include('api_v1.urls_tracking')),
    ])),
    
    # API Version 2 (Advanced Features)
    path('api/v2/', include([
        path('auth/', include('api_v2.urls')),
        path('shipments/', include('api_v2.urls_shipments')),
        path('tracking/', include('api_v2.urls_tracking')),
        path('shifting/', include('api_v2.urls_shifting')),
        path('analytics/', include('api_v2.urls_analytics')),
        path('notifications/', include('api_v2.urls_notifications')),
    ])),
    
    # Service-specific endpoints
    path('users/', include('users.urls')),
    path('shifting/', include('shifting.urls')),
    path('analytics/', include('analytics.urls')),
    path('notifications/', include('notifications.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)