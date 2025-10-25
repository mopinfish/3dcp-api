from django.shortcuts import render
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone

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

import logging
logger = logging.getLogger(__name__)


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
    
    🔧 修正: トークン二重生成の問題を解決
    """
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # 🔧 重要: DBから最新のトークンを取得
        # serializer.save() 内で generate_verification_token() が呼ばれて
        # 新しいトークンがDBに保存されるが、メモリ上のuserオブジェクトは
        # 古いトークンを持っている可能性があるため、DBから再取得する
        user.refresh_from_db()
        verification_token = user.email_verification_token

        logger.info("=" * 80)
        logger.info(f"📝 User Registration: {user.username}")
        logger.info(f"   Email: {user.email}")
        logger.info(f"   Token (from DB): {verification_token}")
        logger.info(f"   Token created at: {user.email_verification_token_created_at}")
        logger.info("=" * 80)

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
        # トークンを文字列に変換（念のため）
        token_str = str(token)
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token_str}"
        
        logger.info(f"📧 Sending verification email to {user.email}")
        logger.info(f"   Token in email: {token_str}")
        logger.info(f"   Verification URL: {verification_url}")
        
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
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )
            logger.info(f"✅ Verification email sent successfully to {user.email}")
        except Exception as e:
            logger.error(f"❌ Failed to send verification email: {e}")
            raise


class SignInAPIView(APIView):
    """
    ログインAPI
    POST /api/v1/auth/signin/
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # デバッグ用ログ出力
        logger.info("=" * 50)
        logger.info("SignIn Request Received")
        logger.info(f"Request Data: {request.data}")
        logger.info(f"Request Content-Type: {request.content_type}")
        logger.info(f"Request Headers: {dict(request.headers)}")
        logger.info("=" * 50)
        
        serializer = SignInSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error(f"Serializer Validation Error: {e}")
            logger.error(f"Serializer Errors: {serializer.errors}")
            raise
        
        user = serializer.validated_data['user']
        
        # トークン認証を使用する場合
        token, created = Token.objects.get_or_create(user=user)
        
        logger.info(f"User {user.username} logged in successfully")
        
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
        except Token.DoesNotExist:
            pass
        
        return Response({
            'message': 'ログアウトしました。'
        }, status=status.HTTP_200_OK)


class EmailVerificationAPIView(APIView):
    """
    メール認証API（完全修正版）
    POST /api/v1/auth/verify-email/
    
    🔧 修正: UUIDトークンの比較ロジックを改善
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # デバッグログ
        logger.info("=" * 80)
        logger.info("📧 Email Verification Request Received")
        logger.info(f"Request Data: {request.data}")
        logger.info(f"Request Method: {request.method}")
        logger.info(f"Current Server Time (timezone.now()): {timezone.now()}")
        logger.info("=" * 80)
        
        serializer = EmailVerificationSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error(f"❌ Serializer Validation Error: {e}")
            logger.error(f"Serializer Errors: {serializer.errors}")
            return Response({
                'error': 'トークンの形式が正しくありません。',
                'details': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        token = serializer.validated_data['token']
        
        # 🔧 UUIDを文字列に変換（ハイフン付きの標準形式）
        token_str = str(token)
        logger.info(f"🔑 Token received: {token_str}")
        logger.info(f"Token type: {type(token)}")
        
        try:
            # 🔧 改善点: UUIDフィールドでの検索を文字列に統一
            user = User.objects.get(email_verification_token=token_str)
            
            logger.info("=" * 80)
            logger.info(f"👤 User found!")
            logger.info(f"  - Username: {user.username}")
            logger.info(f"  - Email: {user.email}")
            logger.info(f"  - Is already verified: {user.is_email_verified}")
            logger.info(f"  - Token in DB: {user.email_verification_token}")
            logger.info(f"  - Token type in DB: {type(user.email_verification_token)}")
            logger.info(f"  - Token created at: {user.email_verification_token_created_at}")
            logger.info("=" * 80)
            
            # すでに認証済みの場合
            if user.is_email_verified:
                logger.info("✅ User is already verified")
                return Response({
                    'message': 'このメールアドレスは既に認証済みです。'
                }, status=status.HTTP_200_OK)
            
            # 🔧 トークンの有効期限チェックを詳細にログ出力
            if user.email_verification_token_created_at:
                current_time = timezone.now()
                token_age = current_time - user.email_verification_token_created_at
                hours_elapsed = token_age.total_seconds() / 3600
                is_valid = token_age.total_seconds() < 86400  # 24時間
                
                logger.info("=" * 80)
                logger.info("⏰ Token Validity Check:")
                logger.info(f"  - Token created at: {user.email_verification_token_created_at}")
                logger.info(f"  - Current time: {current_time}")
                logger.info(f"  - Time elapsed: {token_age}")
                logger.info(f"  - Hours elapsed: {hours_elapsed:.2f}")
                logger.info(f"  - Is valid (< 24h): {is_valid}")
                logger.info("=" * 80)
            
            # verify_emailメソッドでトークン検証と有効期限チェック
            if user.verify_email(token_str):
                logger.info("✅ Email verification successful!")
                return Response({
                    'message': 'メールアドレスの認証が完了しました。',
                    'user': UserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                logger.warning("⚠️ Token expired or invalid")
                return Response({
                    'error': '認証トークンの有効期限が切れています。',
                    'message': '再度サインアップしてください。'
                }, status=status.HTTP_400_BAD_REQUEST)
                
        except User.DoesNotExist:
            logger.error("=" * 80)
            logger.error(f"❌ User with token NOT FOUND")
            logger.error(f"  - Token searched: {token_str}")
            logger.error("=" * 80)
            
            # デバッグのため、全ユーザーのトークンを確認（本番環境では削除推奨）
            if settings.DEBUG:
                all_users = User.objects.all()
                logger.error(f"📊 Total users in database: {all_users.count()}")
                for u in all_users[:5]:  # 最初の5ユーザーのみ
                    logger.error(f"  - User: {u.username}, Token: {u.email_verification_token}")
            
            return Response({
                'error': '無効な認証トークンです。',
                'details': 'トークンが見つかりませんでした。'
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error("=" * 80)
            logger.error(f"❌ Unexpected error during email verification: {e}")
            logger.exception("Full traceback:")
            logger.error("=" * 80)
            return Response({
                'error': 'サーバーエラーが発生しました。',
                'details': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
            new_token = user.generate_verification_token()
            
            logger.info(f"🔄 Resending verification email for {user.username}")
            logger.info(f"   New token: {new_token}")
            
            # 認証メールを再送信
            self.send_verification_email(user, new_token)
            
            return Response({
                'message': '認証メールを再送信しました。'
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': 'このメールアドレスは登録されていません。'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def send_verification_email(self, user, token):
        """
        メール認証用のメールを送信
        """
        token_str = str(token)
        verification_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token_str}"
        
        subject = '【3DCP】メールアドレスの認証(再送)'
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
    
    def update(self, request, *args, **kwargs):
        """
        プロフィール更新（PUT/PATCH）
        デバッグログを追加
        """
        logger.info("=" * 80)
        logger.info("📝 Profile Update Request")
        logger.info(f"  Method: {request.method}")
        logger.info(f"  User: {request.user.username}")
        logger.info(f"  Data: {request.data}")
        logger.info(f"  Files: {request.FILES}")
        logger.info(f"  Content-Type: {request.content_type}")
        logger.info("=" * 80)
        
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            logger.error("=" * 80)
            logger.error("❌ Serializer Validation Error")
            logger.error(f"  Errors: {serializer.errors}")
            logger.error(f"  Exception: {str(e)}")
            logger.error("=" * 80)
            raise
        
        self.perform_update(serializer)
        
        logger.info("=" * 80)
        logger.info("✅ Profile Update Successful")
        logger.info(f"  Updated fields: {list(request.data.keys())}")
        logger.info("=" * 80)
        
        return Response(serializer.data)
    
    def partial_update(self, request, *args, **kwargs):
        """
        部分更新（PATCH）
        """
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

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
        
        if serializer.is_valid():
            # パスワードを変更
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()
            
            return Response({
                'message': 'パスワードを変更しました。'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CheckAuthAPIView(APIView):
    """
    認証状態確認API
    GET /api/v1/auth/check/
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'isAuthenticated': True,
            'user': UserSerializer(request.user).data
        }, status=status.HTTP_200_OK)