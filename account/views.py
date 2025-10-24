from django.shortcuts import render
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .serializers import (
    UserSerializer,
    SignUpSerializer,
    SignInSerializer,
    EmailVerificationSerializer,
    PasswordChangeSerializer
)
from .forms import LoginForm

User = get_user_model()


# ==========================================
# 既存のテンプレートビュー (Django Template用)
# ==========================================

class TopView(LoginRequiredMixin, TemplateView):
    template_name = 'account/top.html'


class MyLoginView(LoginView):
    form_class = LoginForm
    template_name = 'account/login.html'


class MyLogoutView(LogoutView):
    template_name = 'account/logout.html'


# ==========================================
# REST API ビュー (Next.js用)
# ==========================================

class SignUpAPIView(generics.CreateAPIView):
    """
    ユーザー登録API
    POST /api/v1/auth/signup/
    """
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # メール認証用のトークンを生成
        verification_token = user.email_verification_token

        # 認証メールを送信
        self.send_verification_email(user, verification_token)

        return Response({
            'message': '登録が完了しました。メールアドレスに送信された認証リンクをクリックしてください。',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    def send_verification_email(self, user, token):
        """
        メール認証用のメールを送信
        """
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        
        subject = '【3DCP】メールアドレスの認証'
        message = f"""
{user.username} 様

3DCPへのご登録ありがとうございます。

以下のリンクをクリックして、メールアドレスの認証を完了してください:
{verification_url}

このリンクは24時間有効です。

※このメールに心当たりがない場合は、このメールを無視してください。

---
3DCP運営チーム
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class SignInAPIView(APIView):
    """
    ログインAPI
    POST /api/v1/auth/signin/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # トークン認証を使用する場合
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'message': 'ログインに成功しました。',
            'token': token.key,
            'user': UserSerializer(user).data
        }, status=status.HTTP_200_OK)


class SignOutAPIView(APIView):
    """
    ログアウトAPI
    POST /api/v1/auth/signout/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        # トークンを削除
        try:
            request.user.auth_token.delete()
        except:
            pass
        
        return Response({
            'message': 'ログアウトしました。'
        }, status=status.HTTP_200_OK)


class EmailVerificationAPIView(APIView):
    """
    メール認証API
    POST /api/v1/auth/verify-email/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            user = User.objects.get(email_verification_token=token)
            
            if user.is_email_verified:
                return Response({
                    'message': 'このメールアドレスは既に認証済みです。'
                }, status=status.HTTP_200_OK)
            
            if user.verify_email(token):
                return Response({
                    'message': 'メールアドレスの認証が完了しました。',
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': '認証トークンが無効または期限切れです。'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        except User.DoesNotExist:
            return Response({
                'error': '無効な認証トークンです。'
            }, status=status.HTTP_404_NOT_FOUND)


class ResendVerificationEmailAPIView(APIView):
    """
    認証メール再送信API
    POST /api/v1/auth/resend-verification/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({
                'error': 'メールアドレスを入力してください。'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            
            if user.is_email_verified:
                return Response({
                    'message': 'このメールアドレスは既に認証済みです。'
                }, status=status.HTTP_200_OK)
            
            # 新しいトークンを生成
            verification_token = user.generate_verification_token()
            
            # メールを再送信
            self.send_verification_email(user, verification_token)
            
            return Response({
                'message': '認証メールを再送信しました。'
            }, status=status.HTTP_200_OK)
        
        except User.DoesNotExist:
            return Response({
                'error': 'このメールアドレスは登録されていません。'
            }, status=status.HTTP_404_NOT_FOUND)
    
    def send_verification_email(self, user, token):
        """
        メール認証用のメールを送信
        """
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
        
        subject = '【3DCP】メールアドレスの認証（再送）'
        message = f"""
{user.username} 様

メール認証リンクを再送信します。

以下のリンクをクリックして、メールアドレスの認証を完了してください:
{verification_url}

このリンクは24時間有効です。

※このメールに心当たりがない場合は、このメールを無視してください。

---
3DCP運営チーム
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    ユーザー情報取得・更新API
    GET /api/v1/auth/profile/
    PUT /api/v1/auth/profile/
    PATCH /api/v1/auth/profile/
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class PasswordChangeAPIView(APIView):
    """
    パスワード変更API
    POST /api/v1/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        # パスワード変更後、既存のトークンを削除して新しいトークンを発行
        try:
            request.user.auth_token.delete()
        except:
            pass
        
        token = Token.objects.create(user=user)
        
        return Response({
            'message': 'パスワードを変更しました。',
            'token': token.key
        }, status=status.HTTP_200_OK)


class CheckAuthAPIView(APIView):
    """
    認証状態確認API
    GET /api/v1/auth/check/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'authenticated': True,
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)