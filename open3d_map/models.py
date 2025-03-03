import os
from django.contrib.gis.db import models
from django.conf import settings

# Create your models here.
class CulturalProperty(models.Model):
    name = models.CharField(max_length=254)
    name_kana = models.CharField(max_length=254, null=True)
    name_gener = models.CharField(max_length=254, null=True, blank=True)
    name_en = models.CharField(max_length=254, null=True)
    category = models.CharField(max_length=254, null=True, blank=True)
    type = models.CharField(max_length=254)
    place_name = models.CharField(max_length=254, null=True, blank=True)
    address = models.CharField(max_length=254)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    url = models.CharField(max_length=254, null=True)
    note = models.CharField(max_length=4094, null=True)
    geom = models.PointField(srid=6668)

class Movie(models.Model):
    class Meta:
        db_table = 'movies'
        verbose_name = 'Movie'
        verbose_name_plural = 'Movies'

    url = models.CharField(max_length=254)
    title = models.CharField(max_length=254, null=True)
    note = models.CharField(max_length=254, null=True)
    cultural_property = models.ForeignKey(CulturalProperty, related_name='movies', on_delete=models.DO_NOTHING, null=True, blank=True)

def upload_to(instance, filename):
    return os.path.join('images', filename)

class ImageUpload(models.Model):
    media_path = settings.MEDIA_ROOT
    image = models.ImageField(upload_to=upload_to)
    cultural_property = models.ForeignKey(CulturalProperty, related_name='images', on_delete=models.CASCADE, null=True)