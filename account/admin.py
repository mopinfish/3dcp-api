from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth import get_user_model
from django.utils.html import format_html

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    カスタムユーザーモデルの管理画面
    """
    list_display = [
        'username',
        'email',
        'name',
        'is_email_verified_badge',
        'is_staff',
        'is_active',
        'created_at',
    ]
    
    list_filter = [
        'is_staff',
        'is_active',
        'is_email_verified',
        'created_at',
    ]
    
    search_fields = [
        'username',
        'email',
        'name',
    ]
    
    ordering = ['-created_at']
    
    # 詳細画面のフィールド設定
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('個人情報', {
            'fields': ('email', 'name', 'bio', 'avatar')
        }),
        ('メール認証', {
            'fields': (
                'is_email_verified',
                'email_verification_token',
                'email_verification_token_created_at'
            )
        }),
        ('権限', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
        ('重要な日付', {
            'fields': ('last_login', 'date_joined', 'created_at', 'updated_at')
        }),
    )
    
    # 新規作成画面のフィールド設定
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username',
                'email',
                'password1',
                'password2',
                'name',
                'is_staff',
                'is_active'
            ),
        }),
    )
    
    readonly_fields = [
        'email_verification_token',
        'email_verification_token_created_at',
        'last_login',
        'date_joined',
        'created_at',
        'updated_at',
    ]
    
    def is_email_verified_badge(self, obj):
        """
        メール認証状態をバッジで表示
        """
        if obj.is_email_verified:
            return format_html(
                '<span style="background-color: #28a745; color: white; padding: 3px 10px; border-radius: 3px;">認証済み</span>'
            )
        else:
            return format_html(
                '<span style="background-color: #dc3545; color: #000; padding: 3px 10px; border-radius: 3px;">未認証</span>'
            )
    
    is_email_verified_badge.short_description = 'メール認証'