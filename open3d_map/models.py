from django.contrib.gis.db import models

# Create your models here.
class CulturalProperty(models.Model):
    id = models.FloatField(primary_key=True)
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
