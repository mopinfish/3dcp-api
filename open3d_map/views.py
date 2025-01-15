from rest_framework import viewsets
from django_filters import rest_framework as filters 

from .models import Movie, CulturalProperty
from .serializers import MovieSerializer, CulturalPropertySerializer

class CulturalPropertyFilter(filters.FilterSet):
    name = filters.CharFilter(lookup_expr='icontains')
    name_en = filters.CharFilter(lookup_expr='icontains')

    class Meta:
        model = CulturalProperty
        fields = ['name', 'name_en']

class CulturalPropertyViewSet(viewsets.ModelViewSet):
    queryset = CulturalProperty.objects.all()
    serializer_class = CulturalPropertySerializer
    filterset_class = CulturalPropertyFilter
    filterset_fields = ['name', 'name_en']

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer
    filterset_fields = ['cultural_property']
