from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import UserViewSet, TenantViewSet

router = DefaultRouter()
router.register(r'tenants', TenantViewSet, basename='tenant')
router.register(r'users', UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('register/', UserViewSet.as_view({'post': 'register'}), name='register'),
    path('users/me/', UserViewSet.as_view({'get': 'me'}), name='user-me'),
    path('users/bulk/', UserViewSet.as_view({'post': 'bulk_create'}), name='user-bulk-create'),
]