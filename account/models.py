from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid

class User(AbstractUser):
    """
    カスタムユーザーモデル
    メール認証機能を追加
    """
    email = models.EmailField(unique=True, verbose_name='メールアドレス')
    
    # メール認証関連のフィールド
    is_email_verified = models.BooleanField(default=False, verbose_name='メール認証済み')
    email_verification_token = models.UUIDField(
        default=uuid.uuid4, 
        editable=False, 
        verbose_name='メール認証トークン'
    )
    email_verification_token_created_at = models.DateTimeField(
        null=True, 
        blank=True, 
        verbose_name='メール認証トークン作成日時'
    )
    
    # プロフィール情報
    name = models.CharField(max_length=100, blank=True, verbose_name='名前')
    bio = models.TextField(blank=True, verbose_name='自己紹介')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='アバター')
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='作成日時')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新日時')

    class Meta:
        db_table = 'users'
        verbose_name = 'ユーザー'
        verbose_name_plural = 'ユーザー'

    def __str__(self):
        return self.username

    def generate_verification_token(self):
        """
        メール認証用のトークンを生成
        """
        self.email_verification_token = uuid.uuid4()
        self.email_verification_token_created_at = timezone.now()
        self.save()
        return self.email_verification_token

    def verify_email(self, token):
        """
        メール認証を実行
        トークンが一致し、有効期限内(24時間)であれば認証成功
        """
        if str(self.email_verification_token) != str(token):
            return False
        
        # トークンの有効期限チェック(24時間)
        if self.email_verification_token_created_at:
            token_age = timezone.now() - self.email_verification_token_created_at
            if token_age.total_seconds() > 86400:  # 24時間
                return False
        
        self.is_email_verified = True
        self.save()
        return True