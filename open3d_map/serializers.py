from rest_framework import serializers
from .models import Movie, CulturalProperty

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'

class CulturalPropertySerializer(serializers.ModelSerializer):
    movies = MovieSerializer(many=True, read_only=True)

    class Meta:
        model = CulturalProperty
        fields = '__all__'