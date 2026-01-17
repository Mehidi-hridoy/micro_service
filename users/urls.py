from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    # Authentication
    path('register/', views.UserRegistrationView.as_view(), name='user-register'),
    path('login/', views.UserLoginView.as_view(), name='user-login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('logout/', views.UserLogoutView.as_view(), name='user-logout'),
    
    # Profile Management
    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('profile/update/', views.UserUpdateView.as_view(), name='user-update'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    
    # Tenant Management
    path('tenants/', views.TenantListView.as_view(), name='tenant-list'),
    path('tenants/create/', views.TenantCreateView.as_view(), name='tenant-create'),
    path('tenants/<str:tenant_id>/', views.TenantDetailView.as_view(), name='tenant-detail'),
    
    # Sessions
    path('sessions/', views.UserSessionListView.as_view(), name='user-sessions'),
    path('sessions/<int:session_id>/revoke/', views.RevokeSessionView.as_view(), name='revoke-session'),
]