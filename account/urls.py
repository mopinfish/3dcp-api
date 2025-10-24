from django.urls import path
from account.views import (
    # Django Template用ビュー
    TopView,
    MyLoginView,
    MyLogoutView,
    # REST API用ビュー
    SignUpAPIView,
    SignInAPIView,
    SignOutAPIView,
    EmailVerificationAPIView,
    ResendVerificationEmailAPIView,
    UserProfileAPIView,
    PasswordChangeAPIView,
    CheckAuthAPIView,
)

app_name = 'account'

urlpatterns = [
    # Django Template用 (既存)
    path('', TopView.as_view(), name='top'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', MyLogoutView.as_view(), name='logout'),
    
    # REST API用 (新規)
    path('api/signup/', SignUpAPIView.as_view(), name='api_signup'),
    path('api/signin/', SignInAPIView.as_view(), name='api_signin'),
    path('api/signout/', SignOutAPIView.as_view(), name='api_signout'),
    path('api/verify-email/', EmailVerificationAPIView.as_view(), name='api_verify_email'),
    path('api/resend-verification/', ResendVerificationEmailAPIView.as_view(), name='api_resend_verification'),
    path('api/profile/', UserProfileAPIView.as_view(), name='api_profile'),
    path('api/change-password/', PasswordChangeAPIView.as_view(), name='api_change_password'),
    path('api/check/', CheckAuthAPIView.as_view(), name='api_check_auth'),
]