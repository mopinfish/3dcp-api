from django.contrib.gis.db import models

# Create your models here.
class CulturalProperty(models.Model):
    name = models.CharField(max_length=254)
    name_kana = models.CharField(max_length=254, null=True)
    name_gener = models.CharField(max_length=254, null=True)
    name_en = models.CharField(max_length=254, null=True)
    category = models.CharField(max_length=254)
    type = models.CharField(max_length=254)
    place_name = models.CharField(max_length=254, null=True)
    address = models.CharField(max_length=254)
    latitude = models.FloatField(null=True)
    longitude = models.FloatField(null=True)
    url = models.CharField(max_length=254, null=True)
    note = models.CharField(max_length=254, null=True)
    geom = models.PointField(srid=6668)

class Movie(models.Model):
    class Meta:
        db_table = 'movies'
        verbose_name = 'Movie'
        verbose_name_plural = 'Movies'

    cultural_property = models.ForeignKey(CulturalProperty, on_delete=models.CASCADE)
    url = models.CharField(max_length=254)
    title = models.CharField(max_length=254, null=True)
    note = models.CharField(max_length=254, null=True)