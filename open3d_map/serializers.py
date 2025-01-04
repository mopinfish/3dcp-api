from rest_framework import serializers
from .models import Movie, CulturalProperty

class CulturalPropertySerializer(serializers.ModelSerializer):
    class Meta:
        model = CulturalProperty
        fields = '__all__'

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'