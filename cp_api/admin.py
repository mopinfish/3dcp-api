from django.contrib import admin
from .models import CulturalProperty, Movie, ImageUpload, Tag

# Register your models here.

admin.site.register(CulturalProperty)
admin.site.register(Movie)
admin.site.register(ImageUpload)
admin.site.register(Tag)
