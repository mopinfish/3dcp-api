from django_filters import rest_framework as filters
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django_filters.rest_framework import NumberFilter, CharFilter

from .models import CulturalProperty

class CulturalPropertyFilter(filters.FilterSet):
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

    class Meta:
        model = CulturalProperty
        fields = ['name', 'name_en', 'has_movies', 'lat', 'lon', 'distance', 'tag_id', 'tag_name']

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
