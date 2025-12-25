"""
cp_api/filters.py

文化財のフィルタリング

✅ 変更内容:
- created_byフィルターを追加
"""

from django_filters import rest_framework as filters
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django_filters.rest_framework import NumberFilter, CharFilter

from .models import CulturalProperty


class CulturalPropertyFilter(filters.FilterSet):
    """文化財フィルター"""
    
    name = filters.CharFilter(lookup_expr='icontains')
    name_en = filters.CharFilter(lookup_expr='icontains')
    has_movies = filters.BooleanFilter(field_name='movies', lookup_expr='isnull', exclude=True)
    
    # 緯度・経度・距離のフィルタ
    lat = NumberFilter(method='filter_by_distance')
    lon = NumberFilter(method='filter_by_distance')
    distance = NumberFilter(method='filter_by_distance')

    # タグフィルタ
    tag_id = NumberFilter(method='filter_by_tag_id')
    tag_name = CharFilter(method='filter_by_tag_name')

    # ✅ 新規追加: 作成者フィルター
    created_by = NumberFilter(field_name='created_by__id')
    created_by_username = CharFilter(field_name='created_by__username', lookup_expr='exact')

    class Meta:
        model = CulturalProperty
        fields = [
            'name', 
            'name_en', 
            'has_movies', 
            'lat', 
            'lon', 
            'distance', 
            'tag_id', 
            'tag_name',
            'created_by',
            'created_by_username'
        ]

    def filter_by_distance(self, queryset, name, value):
        """
        指定した緯度(lat)、経度(lon)、半径(distance)内のデータのみを取得
        """
        lat = self.data.get('lat')
        lon = self.data.get('lon')
        distance = self.data.get('distance')

        if lat and lon and distance:
            try:
                user_location = Point(float(lon), float(lat), srid=4326)
                return queryset.annotate(
                    distance=Distance('geom', user_location)
                ).filter(distance__lte=float(distance))
            except ValueError:
                return queryset
        return queryset

    def filter_by_tag_id(self, queryset, name, value):
        """タグIDでフィルタリング"""
        return queryset.filter(tags__id=value)

    def filter_by_tag_name(self, queryset, name, value):
        """タグ名でフィルタリング"""
        return queryset.filter(tags__name__icontains=value)


class MovieFilter(filters.FilterSet):
    """ムービーフィルター"""
    
    title = filters.CharFilter(lookup_expr='icontains')
    cultural_property = NumberFilter(field_name='cultural_property__id')
    created_by = NumberFilter(field_name='created_by__id')
    
    class Meta:
        from .models import Movie
        model = Movie
        fields = ['title', 'cultural_property', 'created_by']
