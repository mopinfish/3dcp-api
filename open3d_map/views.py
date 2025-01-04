from rest_framework import viewsets

from .models import Movie, CulturalProperty
from .serializers import MovieSerializer, CulturalPropertySerializer

class MovieViewSet(viewsets.ModelViewSet):
    queryset = Movie.objects.all()
    serializer_class = MovieSerializer

class CulturalPropertyViewSet(viewsets.ModelViewSet):
    queryset = CulturalProperty.objects.all()
    serializer_class = CulturalPropertySerializer

# Create your views here.
