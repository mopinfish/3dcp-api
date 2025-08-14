from django.contrib import admin
from .models import CulturalProperty, Movie, ImageUpload, Tag

# Register your models here.

@admin.register(CulturalProperty)
class CulturalPropertyAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)  # 名前の全文検索が可能に

admin.site.register(Movie)
admin.site.register(ImageUpload)
admin.site.register(Tag)
