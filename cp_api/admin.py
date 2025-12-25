"""
cp_api/admin.py

管理画面の設定

✅ 変更内容:
- CulturalPropertyAdminにcreated_by, created_at, updated_atを表示
- MovieAdminを追加
"""

from django.contrib import admin
from .models import CulturalProperty, Movie, ImageUpload, Tag


@admin.register(CulturalProperty)
class CulturalPropertyAdmin(admin.ModelAdmin):
    """文化財の管理画面"""
    list_display = (
        'name', 
        'type', 
        'category', 
        'address', 
        'created_by', 
        'created_at', 
        'updated_at'
    )
    list_filter = ('type', 'category', 'created_at')
    search_fields = ('name', 'name_kana', 'name_en', 'address')
    readonly_fields = ('created_at', 'updated_at', 'geom')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('name', 'name_kana', 'name_gener', 'name_en')
        }),
        ('分類', {
            'fields': ('type', 'category', 'tags')
        }),
        ('位置情報', {
            'fields': ('place_name', 'address', 'latitude', 'longitude', 'geom')
        }),
        ('その他', {
            'fields': ('url', 'note')
        }),
        ('メタ情報', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    filter_horizontal = ('tags',)
    
    def save_model(self, request, obj, form, change):
        """
        保存時にcreated_byを設定
        """
        if not change:  # 新規作成時
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    """ムービーの管理画面"""
    list_display = (
        'title', 
        'cultural_property', 
        'url', 
        'created_by', 
        'created_at', 
        'updated_at'
    )
    list_filter = ('created_at', 'cultural_property')
    search_fields = ('title', 'url', 'note')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('基本情報', {
            'fields': ('title', 'url', 'note')
        }),
        ('関連', {
            'fields': ('cultural_property',)
        }),
        ('メタ情報', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """
        保存時にcreated_byを設定
        """
        if not change:  # 新規作成時
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(ImageUpload)
class ImageUploadAdmin(admin.ModelAdmin):
    """画像アップロードの管理画面"""
    list_display = ('id', 'image', 'cultural_property')
    list_filter = ('cultural_property',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """タグの管理画面"""
    list_display = ('name', 'description')
    search_fields = ('name', 'description')
