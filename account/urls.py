from django.urls import path
from account.views import (
    # Django Template用
    TopView,
    MyLoginView,
    MyLogoutView,
    
    # REST API用
    SignUpAPIView,
    SignInAPIView,
    SignOutAPIView,
    EmailVerificationAPIView,
    ResendVerificationEmailAPIView,
    UserProfileAPIView,
    PasswordChangeAPIView,
    CheckAuthAPIView,
    ActiveUsersAPIView,  # ✅ NEW
)

app_name = 'account'

urlpatterns = [
    # Django Template用 (既存)
    path('', TopView.as_view(), name='top'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', MyLogoutView.as_view(), name='logout'),
    
    # REST API用 (新規) - api/ プレフィックスを削除
    path('signup/', SignUpAPIView.as_view(), name='api_signup'),
    path('signin/', SignInAPIView.as_view(), name='api_signin'),
    path('signout/', SignOutAPIView.as_view(), name='api_signout'),
    path('verify-email/', EmailVerificationAPIView.as_view(), name='api_verify_email'),
    path('resend-verification/', ResendVerificationEmailAPIView.as_view(), name='api_resend_verification'),
    path('profile/', UserProfileAPIView.as_view(), name='api_profile'),
    path('change-password/', PasswordChangeAPIView.as_view(), name='api_change_password'),
    path('check/', CheckAuthAPIView.as_view(), name='api_check_auth'),
    
    # ✅ NEW: アクティブユーザーAPI
    path('active-users/', ActiveUsersAPIView.as_view(), name='api_active_users'),
]
