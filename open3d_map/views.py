from rest_framework import viewsets

from .models import Movie, CulturalProperty, Tag
from .serializers import MovieSerializer, CulturalPropertySerializer, TagSerializer
from .filters import CulturalPropertyFilter

class CulturalPropertyViewSet(viewsets.ModelViewSet):
    queryset = CulturalProperty.objects.all().prefetch_related('movies').prefetch_related('images').prefetch_related('tags')
    serializer_class = CulturalPropertySerializer
    filterset_class = CulturalPropertyFilter
    filterset_fields = ['name', 'name_en', 'movies']

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all().prefetch_related('cultural_property')
    serializer_class = MovieSerializer
    filterset_fields = ['title']

class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all().prefetch_related('cultural_properties')
    serializer_class = TagSerializer
    filterset_fields = ['name']
