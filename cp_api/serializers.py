"""
cp_api/serializers.py

文化財（CulturalProperty）とムービー（Movie）のシリアライザー

✅ 変更内容:
- CulturalPropertySerializerにcreated_by, created_at, updated_atを追加
- MovieSerializerにcreated_by, created_at, updated_atを追加
- MovieSerializerにthumbnail_urlを追加（サムネイル画像URL）
- 作成・更新用のシリアライザーを追加
- created_byは読み取り専用（自動設定）
"""

import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Movie, CulturalProperty, ImageUpload, Tag

User = get_user_model()


class UserBriefSerializer(serializers.ModelSerializer):
    """
    ユーザー情報の簡易シリアライザー（作成者表示用）
    """
    class Meta:
        model = User
        fields = ['id', 'username', 'name']
        read_only_fields = ['id', 'username', 'name']


class TagSerializer(serializers.ModelSerializer):
    """タグシリアライザー"""
    class Meta:
        model = Tag
        fields = '__all__'


class MovieSerializer(serializers.ModelSerializer):
    """
    ムービーシリアライザー（読み取り用）
    
    ✅ 変更: thumbnail_urlフィールドを追加
    """
    created_by = UserBriefSerializer(read_only=True)
    thumbnail_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Movie
        fields = [
            'id', 
            'url', 
            'title', 
            'note', 
            'cultural_property',
            'created_by',
            'created_at',
            'updated_at',
            'thumbnail_url',  # ✅ 追加
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at', 'thumbnail_url']

    def get_thumbnail_url(self, obj):
        """
        サムネイルURLを取得
        
        優先順位:
        1. DBに保存されたサムネイル画像
        2. フォールバック: Luma CDNの直接参照
        """
        # DBに保存されたサムネイルがある場合
        if obj.thumbnail:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.thumbnail.url)
            return obj.thumbnail.url
        
        # フォールバック: Luma CDNを直接参照
        if obj.url and 'lumalabs.ai' in obj.url:
            match = re.search(r'lumalabs\.ai/capture/([a-zA-Z0-9-]+)', obj.url)
            if match:
                return f"https://cdn.lumalabs.ai/captures/{match.group(1)}/thumbnail.jpg"
        
        return None


class MovieCreateSerializer(serializers.ModelSerializer):
    """
    ムービーシリアライザー（作成・更新用）
    """
    class Meta:
        model = Movie
        fields = [
            'id',
            'url', 
            'title', 
            'note', 
            'cultural_property'
        ]
        read_only_fields = ['id']

    def validate_url(self, value):
        """
        URLのバリデーション
        """
        if not value:
            raise serializers.ValidationError("URLは必須です")
        return value


class ImageUploadSerializer(serializers.ModelSerializer):
    """画像アップロードシリアライザー"""
    class Meta:
        model = ImageUpload
        fields = '__all__'


class CulturalPropertySerializer(serializers.ModelSerializer):
    """
    文化財シリアライザー（読み取り用）
    """
    movies = MovieSerializer(many=True, read_only=True)
    images = ImageUploadSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    created_by = UserBriefSerializer(read_only=True)

    class Meta:
        model = CulturalProperty
        fields = [
            'id',
            'name',
            'name_kana',
            'name_gener',
            'name_en',
            'category',
            'type',
            'place_name',
            'address',
            'latitude',
            'longitude',
            'url',
            'note',
            'geom',
            'tags',
            'movies',
            'images',
            'created_by',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'geom', 'created_by', 'created_at', 'updated_at']


class CulturalPropertyCreateSerializer(serializers.ModelSerializer):
    """
    文化財シリアライザー（作成・更新用）
    
    - geomはlatitude/longitudeから自動生成されるため、ここでは受け取らない
    - tagsはIDの配列で受け取る
    """
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
        required=False
    )

    class Meta:
        model = CulturalProperty
        fields = [
            'id',
            'name',
            'name_kana',
            'name_gener',
            'name_en',
            'category',
            'type',
            'place_name',
            'address',
            'latitude',
            'longitude',
            'url',
            'note',
            'tags'
        ]
        read_only_fields = ['id']

    def validate_name(self, value):
        """名称のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("名称は必須です")
        return value.strip()

    def validate_type(self, value):
        """種別のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("種別は必須です")
        return value.strip()

    def validate_address(self, value):
        """住所のバリデーション"""
        if not value or not value.strip():
            raise serializers.ValidationError("住所は必須です")
        return value.strip()
