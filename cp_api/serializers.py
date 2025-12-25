"""
cp_api/serializers.py

文化財（CulturalProperty）とムービー（Movie）のシリアライザー

✅ 変更内容:
- CulturalPropertySerializerにcreated_by, created_at, updated_atを追加
- MovieSerializerにcreated_by, created_at, updated_atを追加
- 作成・更新用のシリアライザーを追加
- created_byは読み取り専用（自動設定）
"""

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
    """
    created_by = UserBriefSerializer(read_only=True)
    
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
            'updated_at'
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']


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

    def validate(self, data):
        """
        全体のバリデーション
        """
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        # 新規作成時は緯度・経度が必須
        if self.instance is None:  # 新規作成
            if latitude is None or longitude is None:
                raise serializers.ValidationError({
                    'latitude': '緯度は必須です',
                    'longitude': '経度は必須です'
                })
        
        # 緯度・経度の範囲チェック
        if latitude is not None:
            if not (-90 <= latitude <= 90):
                raise serializers.ValidationError({
                    'latitude': '緯度は-90から90の範囲で指定してください'
                })
        
        if longitude is not None:
            if not (-180 <= longitude <= 180):
                raise serializers.ValidationError({
                    'longitude': '経度は-180から180の範囲で指定してください'
                })
        
        return data


class CulturalPropertyWithMoviesCreateSerializer(serializers.Serializer):
    """
    文化財とムービーを同時に作成するためのシリアライザー
    
    フロントエンドから文化財と複数のムービーを一度に登録する際に使用
    """
    cultural_property = CulturalPropertyCreateSerializer()
    movies = MovieCreateSerializer(many=True, required=False)

    def create(self, validated_data):
        """
        文化財とムービーを作成
        """
        movies_data = validated_data.pop('movies', [])
        cultural_property_data = validated_data.pop('cultural_property')
        
        # タグを分離
        tags = cultural_property_data.pop('tags', [])
        
        # 文化財を作成
        cultural_property = CulturalProperty.objects.create(**cultural_property_data)
        
        # タグを設定
        if tags:
            cultural_property.tags.set(tags)
        
        # ムービーを作成
        for movie_data in movies_data:
            Movie.objects.create(
                cultural_property=cultural_property,
                created_by=cultural_property.created_by,
                **movie_data
            )
        
        return cultural_property
