from django.contrib import admin
from .models import CulturalProperty, Movie, ImageUpload

# Register your models here.

admin.site.register(CulturalProperty)
admin.site.register(Movie)
admin.site.register(ImageUpload)
