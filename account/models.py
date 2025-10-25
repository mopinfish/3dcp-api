from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)


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
        
        logger.info(f"Generated new verification token for user {self.username}: {self.email_verification_token}")
        
        return self.email_verification_token

    def verify_email(self, token):
        """
        メール認証を実行（改善版）
        トークンが一致し、有効期限内(24時間)であれば認証成功
        """
        logger.info("=" * 80)
        logger.info(f"🔐 Verifying email for user: {self.username}")
        
        # 🔧 改善点1: トークン比較を文字列で統一
        # UUIDオブジェクトと文字列の両方に対応
        token_str = str(token)
        db_token_str = str(self.email_verification_token)
        
        logger.info(f"  - Token from request: {token_str}")
        logger.info(f"  - Token from database: {db_token_str}")
        logger.info(f"  - Tokens match: {token_str == db_token_str}")
        
        # トークンが一致しない場合
        if token_str != db_token_str:
            logger.warning(f"❌ Token mismatch for user {self.username}")
            logger.warning(f"  - Expected: {db_token_str}")
            logger.warning(f"  - Got: {token_str}")
            return False
        
        logger.info("✅ Token matches!")
        
        # 🔧 改善点2: トークンの有効期限チェックを詳細にログ出力
        if self.email_verification_token_created_at:
            current_time = timezone.now()
            token_age = current_time - self.email_verification_token_created_at
            hours_elapsed = token_age.total_seconds() / 3600
            is_expired = token_age.total_seconds() > 86400  # 24時間
            
            logger.info("⏰ Checking token expiration:")
            logger.info(f"  - Token created at: {self.email_verification_token_created_at}")
            logger.info(f"  - Current time: {current_time}")
            logger.info(f"  - Time elapsed: {token_age}")
            logger.info(f"  - Hours elapsed: {hours_elapsed:.2f} hours")
            logger.info(f"  - Is expired (> 24h): {is_expired}")
            
            if is_expired:
                logger.warning(f"❌ Token expired for user {self.username}")
                logger.warning(f"  - Token was created {hours_elapsed:.2f} hours ago")
                logger.info("=" * 80)
                return False
        else:
            logger.warning(f"⚠️ Token created_at is None for user {self.username}")
            logger.info("=" * 80)
            return False
        
        # 認証成功
        logger.info(f"✅ Email verification successful for user {self.username}")
        self.is_email_verified = True
        self.save()
        logger.info("=" * 80)
        
        return True