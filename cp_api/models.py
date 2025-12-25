"""
cp_api/models.py

文化財（CulturalProperty）とムービー（Movie）のモデル定義

✅ 変更内容:
- CulturalPropertyモデルにcreated_by, created_at, updated_atフィールドを追加
- Movieモデルにcreated_by, created_at, updated_atフィールドを追加
- 既存データとの互換性のため、created_byはnull=True, blank=Trueに設定
"""

import os
from django.conf import settings
from django.contrib.gis.db import models


class Tag(models.Model):
    """タグモデル"""
    name = models.CharField(max_length=100, unique=True)  # タグ名
    description = models.TextField(null=True, blank=True)  # タグの説明

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'タグ'
        verbose_name_plural = 'タグ'


class CulturalProperty(models.Model):
    """文化財モデル"""
    name = models.CharField(max_length=254, verbose_name='名称')
    name_kana = models.CharField(max_length=254, null=True, blank=True, verbose_name='ふりがな')
    name_gener = models.CharField(max_length=254, null=True, blank=True, verbose_name='一般名称')
    name_en = models.CharField(max_length=254, null=True, blank=True, verbose_name='英語名')
    category = models.CharField(max_length=254, null=True, blank=True, verbose_name='カテゴリ')
    type = models.CharField(max_length=254, verbose_name='種別')
    place_name = models.CharField(max_length=254, null=True, blank=True, verbose_name='場所名')
    address = models.CharField(max_length=254, verbose_name='住所')
    latitude = models.FloatField(null=True, blank=True, verbose_name='緯度')
    longitude = models.FloatField(null=True, blank=True, verbose_name='経度')
    url = models.CharField(max_length=254, null=True, blank=True, verbose_name='参考URL')
    note = models.CharField(max_length=4094, null=True, blank=True, verbose_name='備考')
    geom = models.PointField(srid=6668, verbose_name='ジオメトリ')

    # タグとのリレーション
    tags = models.ManyToManyField(
        Tag, 
        related_name='cultural_properties', 
        blank=True,
        verbose_name='タグ'
    )

    # ✅ 新規追加: 作成者フィールド
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cultural_properties',
        verbose_name='作成者'
    )

    # ✅ 新規追加: タイムスタンプフィールド
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,  # 既存データとの互換性のためnull=True
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,  # 既存データとの互換性のためnull=True
        verbose_name='更新日時'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = '文化財'
        verbose_name_plural = '文化財'
        ordering = ['-created_at', '-id']


class Movie(models.Model):
    """ムービー（3D映像）モデル"""
    url = models.CharField(max_length=254, verbose_name='URL')
    title = models.CharField(max_length=254, null=True, blank=True, verbose_name='タイトル')
    note = models.CharField(max_length=254, null=True, blank=True, verbose_name='備考')
    cultural_property = models.ForeignKey(
        CulturalProperty, 
        related_name='movies', 
        on_delete=models.SET_NULL,  # DO_NOTHINGからSET_NULLに変更（安全性向上）
        null=True, 
        blank=True,
        verbose_name='文化財'
    )

    # ✅ 新規追加: 作成者フィールド
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movies',
        verbose_name='作成者'
    )

    # ✅ 新規追加: タイムスタンプフィールド
    created_at = models.DateTimeField(
        auto_now_add=True,
        null=True,  # 既存データとの互換性のためnull=True
        verbose_name='作成日時'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        null=True,  # 既存データとの互換性のためnull=True
        verbose_name='更新日時'
    )

    def __str__(self):
        return self.title or f"Movie #{self.id}"

    class Meta:
        db_table = 'movies'
        verbose_name = 'ムービー'
        verbose_name_plural = 'ムービー'
        ordering = ['-created_at', '-id']


def upload_to(instance, filename):
    """画像アップロード先のパスを生成"""
    return os.path.join('images', filename)


class ImageUpload(models.Model):
    """画像アップロードモデル"""
    media_path = settings.MEDIA_ROOT
    image = models.ImageField(upload_to=upload_to, verbose_name='画像')
    cultural_property = models.ForeignKey(
        CulturalProperty, 
        related_name='images', 
        on_delete=models.CASCADE, 
        null=True,
        verbose_name='文化財'
    )

    def __str__(self):
        return f"Image for {self.cultural_property.name if self.cultural_property else 'Unknown'}"

    class Meta:
        verbose_name = '画像'
        verbose_name_plural = '画像'
