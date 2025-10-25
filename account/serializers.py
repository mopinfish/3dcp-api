from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    ユーザー情報のシリアライザー
    """
    class Meta:
        model = User
        fields = [
            'id', 
            'username', 
            'email', 
            'name', 
            'bio', 
            'avatar',
            'is_email_verified',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'is_email_verified', 'created_at', 'updated_at']


class SignUpSerializer(serializers.ModelSerializer):
    """
    サインアップ用のシリアライザー
    """
    password = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True, 
        required=True, 
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password_confirm', 'name']

    def validate_email(self, value):
        """
        メールアドレスの重複チェック
        """
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('このメールアドレスは既に登録されています。')
        return value

    def validate_username(self, value):
        """
        ユーザー名の重複チェック
        """
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError('このユーザー名は既に使用されています。')
        return value

    def validate(self, data):
        """
        パスワードの一致チェックとバリデーション
        """
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': 'パスワードが一致しません。'
            })
        
        # Djangoのパスワードバリデーション
        try:
            validate_password(data['password'])
        except ValidationError as e:
            raise serializers.ValidationError({'password': list(e.messages)})
        
        return data

    def create(self, validated_data):
        """
        ユーザーの作成
        """
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            name=validated_data.get('name', '')
        )
        # メール認証トークンを生成
        user.generate_verification_token()
        return user


class SignInSerializer(serializers.Serializer):
    """
    サインイン用のシリアライザー
    メールアドレスまたはユーザー名の両方でログイン可能
    """
    username = serializers.CharField(required=True)
    password = serializers.CharField(
        required=True, 
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        """
        認証チェック
        メールアドレスまたはユーザー名のどちらでもログイン可能
        """
        username_or_email = data.get('username')
        password = data.get('password')

        if username_or_email and password:
            # まずユーザー名で認証を試みる
            user = authenticate(username=username_or_email, password=password)
            
            # ユーザー名での認証が失敗した場合、メールアドレスで再試行
            if not user:
                try:
                    # メールアドレスでユーザーを検索
                    user_obj = User.objects.get(email=username_or_email)
                    # ユーザー名を使って認証
                    user = authenticate(username=user_obj.username, password=password)
                except User.DoesNotExist:
                    pass
            
            # 認証に失敗した場合
            if not user:
                raise serializers.ValidationError(
                    'ユーザー名/メールアドレスまたはパスワードが正しくありません。'
                )
            
            # アカウントが無効化されている場合
            if not user.is_active:
                raise serializers.ValidationError(
                    'このアカウントは無効化されています。'
                )
            
            data['user'] = user
        else:
            raise serializers.ValidationError(
                'ユーザー名/メールアドレスとパスワードは必須です。'
            )
        
        return data


class EmailVerificationSerializer(serializers.Serializer):
    """
    メール認証用のシリアライザー
    """
    token = serializers.UUIDField(required=True)


class PasswordChangeSerializer(serializers.Serializer):
    """
    パスワード変更用のシリアライザー
    """
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate_old_password(self, value):
        """
        現在のパスワードの確認
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('現在のパスワードが正しくありません。')
        return value

    def validate(self, data):
        """
        新しいパスワードの一致チェックとバリデーション
        """
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': '新しいパスワードが一致しません。'
            })
        
        # Djangoのパスワードバリデーション
        try:
            validate_password(data['new_password'])
        except ValidationError as e:
            raise serializers.ValidationError({'new_password': list(e.messages)})
        
        return data