from rest_framework import viewsets
from django_filters import rest_framework as filters 

from .models import Movie, CulturalProperty
from .serializers import MovieSerializer, CulturalPropertySerializer

class CulturalPropertyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    name_en = filters.CharFilter(lookup_expr='icontains')
    has_movies = filters.BooleanFilter(field_name='movies', lookup_expr='isnull', exclude=True)

    class Meta:
        model = CulturalProperty
        fields = ['name', 'name_en', 'has_movies']

class CulturalPropertyViewSet(viewsets.ModelViewSet):
    queryset = CulturalProperty.objects.all().prefetch_related('movies')
    serializer_class = CulturalPropertySerializer
    filterset_class = CulturalPropertyFilter
    filterset_fields = ['name', 'name_en', 'movies']

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().prefetch_related('cultural_property')
    serializer_class = MovieSerializer
    filterset_fields = ['title']
