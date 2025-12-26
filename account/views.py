from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.db.models import Count

from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token

from .serializers import (
    UserSerializer,
    SignUpSerializer,
    SignInSerializer,
    EmailVerificationSerializer,
    PasswordChangeSerializer,
    ActiveUserSerializer,
    PublicUserProfileSerializer,  # ✅ NEW: Phase 3
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
    
    リクエストボディ:
        - username: ユーザー名 (必須)
        - email: メールアドレス (必須)
        - password: パスワード (必須)
        - password_confirm: パスワード確認 (必須)
        - name: 表示名 (オプション)
    
    レスポンス:
        - user: ユーザー情報
        - token: 認証トークン
        - message: メッセージ
    """
    serializer_class = SignUpSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # 認証トークンを生成
        token, _ = Token.objects.get_or_create(user=user)
        
        # メール認証メールを送信
        self.send_verification_email(user, user.email_verification_token)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key,
            'message': 'アカウントを作成しました。メールアドレスの認証をお願いします。'
        }, status=status.HTTP_201_CREATED)

    def send_verification_email(self, user, token):
        """
        メール認証メールを送信
        """
        frontend_url = settings.FRONTEND_URL
        verification_url = f"{frontend_url}/verify-email?token={token}"
        
        subject = '【3D文化財共有サイト】メールアドレスの認証'
        
        # HTMLメール
        html_message = render_to_string('account/emails/verification_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        
        # テキストメール
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")


class SignInAPIView(APIView):
    """
    ログインAPI
    POST /api/v1/auth/signin/
    
    リクエストボディ:
        - username: ユーザー名またはメールアドレス
        - password: パスワード
    
    レスポンス:
        - user: ユーザー情報
        - token: 認証トークン
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SignInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # セッション認証
        login(request, user)
        
        # トークン認証用のトークンを取得または作成
        token, _ = Token.objects.get_or_create(user=user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': token.key
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
        
        # セッションをクリア
        logout(request)
        
        return Response({
            'message': 'ログアウトしました。'
        }, status=status.HTTP_200_OK)


class EmailVerificationAPIView(APIView):
    """
    メール認証API
    POST /api/v1/auth/verify-email/
    
    リクエストボディ:
        - token: メール認証トークン (UUID)
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = EmailVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            user = User.objects.get(email_verification_token=token)
            
            # トークンの有効期限チェック（24時間）
            if user.email_verification_token_created_at:
                token_age = timezone.now() - user.email_verification_token_created_at
                if token_age.total_seconds() > 86400:  # 24時間 = 86400秒
                    return Response({
                        'error': 'トークンの有効期限が切れています。再度認証メールを送信してください。'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # メール認証を完了
            user.is_email_verified = True
            user.email_verification_token = None
            user.email_verification_token_created_at = None
            user.save()
            
            return Response({
                'message': 'メールアドレスの認証が完了しました。',
                'user': UserSerializer(user).data
            }, status=status.HTTP_200_OK)
            
        except User.DoesNotExist:
            return Response({
                'error': '無効なトークンです。'
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationEmailAPIView(APIView):
    """
    認証メール再送信API
    POST /api/v1/auth/resend-verification/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        
        if user.is_email_verified:
            return Response({
                'error': 'このアカウントは既に認証されています。'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 新しいトークンを生成
        user.generate_verification_token()
        
        # メール送信
        self.send_verification_email(user, user.email_verification_token)
        
        return Response({
            'message': '認証メールを再送信しました。'
        }, status=status.HTTP_200_OK)

    def send_verification_email(self, user, token):
        """
        メール認証メールを送信
        """
        frontend_url = settings.FRONTEND_URL
        verification_url = f"{frontend_url}/verify-email?token={token}"
        
        subject = '【3D文化財共有サイト】メールアドレスの認証'
        
        # HTMLメール
        html_message = render_to_string('account/emails/verification_email.html', {
            'user': user,
            'verification_url': verification_url,
        })
        
        # テキストメール
        plain_message = strip_tags(html_message)
        
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Verification email sent to {user.email}")
        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {e}")


class UserProfileAPIView(generics.RetrieveUpdateAPIView):
    """
    ユーザープロフィールAPI
    GET /api/v1/auth/profile/ - プロフィール取得
    PUT/PATCH /api/v1/auth/profile/ - プロフィール更新
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({
            'user': serializer.data,
            'message': 'プロフィールを更新しました。'
        }, status=status.HTTP_200_OK)


class PasswordChangeAPIView(APIView):
    """
    パスワード変更API
    POST /api/v1/auth/change-password/
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # トークンを再生成（セキュリティのため）
            Token.objects.filter(user=user).delete()
            new_token = Token.objects.create(user=user)
            
            return Response({
                'message': 'パスワードを変更しました。',
                'token': new_token.key
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


# ==========================================
# ✅ NEW: アクティブユーザーAPI
# ==========================================

class ActiveUsersAPIView(APIView):
    """
    アクティブユーザー一覧取得API
    GET /api/v1/auth/active-users/
    
    文化財またはムービーを登録しているユーザーを
    登録数の多い順に取得
    
    クエリパラメータ:
        - limit: 取得件数（デフォルト: 5、最大: 20）
    
    レスポンス:
        - users: アクティブユーザー一覧
            - id: ユーザーID
            - username: ユーザー名
            - name: 表示名
            - avatar: アバター画像URL
            - cultural_property_count: 文化財登録数
            - movie_count: ムービー登録数
            - total_count: 合計登録数
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # クエリパラメータからlimitを取得
        try:
            limit = int(request.query_params.get('limit', 5))
            limit = min(max(limit, 1), 20)  # 1〜20の範囲に制限
        except (ValueError, TypeError):
            limit = 5
        
        # 文化財またはムービーを登録しているユーザーを取得
        # Countで登録数を集計し、合計数でソート
        users = User.objects.annotate(
            cultural_property_count=Count('cultural_properties', distinct=True),
            movie_count=Count('movies', distinct=True),
        ).filter(
            # 文化財またはムービーを1件以上登録しているユーザー
            cultural_property_count__gt=0
        ).order_by(
            '-cultural_property_count',  # 文化財登録数の降順
            '-movie_count',  # ムービー登録数の降順
        )[:limit]
        
        # シリアライズ
        serializer = ActiveUserSerializer(users, many=True, context={'request': request})
        
        return Response({
            'users': serializer.data,
            'count': len(serializer.data)
        }, status=status.HTTP_200_OK)


# ==========================================
# ✅ NEW: 公開ユーザープロフィールAPI (Phase 3)
# ==========================================

class PublicUserProfileAPIView(APIView):
    """
    公開ユーザープロフィール取得API
    GET /api/v1/auth/users/<user_id>/
    
    他のユーザーが閲覧可能な公開プロフィール情報を取得
    
    パスパラメータ:
        - user_id: ユーザーID
    
    レスポンス:
        - id: ユーザーID
        - username: ユーザー名
        - name: 表示名
        - bio: 自己紹介
        - avatar: アバター画像
        - avatar_url: アバター画像URL（絶対パス）
        - cultural_property_count: 文化財登録数
        - movie_count: ムービー登録数
        - date_joined: 登録日
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, user_id):
        # ユーザーを取得（存在しない場合は404）
        user = get_object_or_404(User, id=user_id, is_active=True)
        
        # 登録数を集計
        user = User.objects.annotate(
            cultural_property_count=Count('cultural_properties', distinct=True),
            movie_count=Count('movies', distinct=True),
        ).get(id=user_id)
        
        # シリアライズ
        serializer = PublicUserProfileSerializer(user, context={'request': request})
        
        return Response(serializer.data, status=status.HTTP_200_OK)
