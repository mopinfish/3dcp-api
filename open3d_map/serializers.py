from rest_framework import serializers
from .models import Movie, CulturalProperty, ImageUpload, Tag

class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'

class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = '__all__'

class ImageUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageUpload
        fields = '__all__'

class CulturalPropertySerializer(serializers.ModelSerializer):
    movies = MovieSerializer(many=True, read_only=True)
    images = ImageUploadSerializer(many=True, read_only=True)
    tags = TagSerializer(many=True, read_only=True)  # タグ情報を含める

    class Meta:
        model = CulturalProperty
        fields = '__all__'
