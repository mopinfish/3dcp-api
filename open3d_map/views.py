from rest_framework import viewsets
from django_filters import rest_framework as filters 
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.geos import Point
from django_filters.rest_framework import NumberFilter

from .models import Movie, CulturalProperty
from .serializers import MovieSerializer, CulturalPropertySerializer

class CulturalPropertyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    name_en = filters.CharFilter(lookup_expr='icontains')
    has_movies = filters.BooleanFilter(field_name='movies', lookup_expr='isnull', exclude=True)
    
    # 緯度・経度・距離のフィルタを追加
    lat = NumberFilter(method='filter_by_distance')
    lon = NumberFilter(method='filter_by_distance')
    distance = NumberFilter(method='filter_by_distance')

    class Meta:
        model = CulturalProperty
        fields = ['name', 'name_en', 'has_movies', 'lat', 'lon', 'distance']

    def filter_by_distance(self, queryset, name, value):
        """
        指定した緯度(lat)、経度(lon)、半径(distance)内のデータのみを取得
        """
        lat = self.data.get('lat')
        lon = self.data.get('lon')
        distance = self.data.get('distance')

        if lat and lon and distance:
            try:
                user_location = Point(float(lon), float(lat), srid=4326)  # ユーザーの座標
                return queryset.annotate(
                    distance=Distance('geom', user_location)
                ).filter(distance__lte=float(distance))  # 指定距離内のデータを取得
            except ValueError:
                return queryset  # 不正な値が渡された場合は、フィルタ適用せず返す
        return queryset

class CulturalPropertyViewSet(viewsets.ModelViewSet):
    queryset = CulturalProperty.objects.all().prefetch_related('movies').prefetch_related('images')
    serializer_class = CulturalPropertySerializer
    filterset_class = CulturalPropertyFilter
    filterset_fields = ['name', 'name_en', 'movies']

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().prefetch_related('cultural_property')
    serializer_class = MovieSerializer
    filterset_fields = ['title']
