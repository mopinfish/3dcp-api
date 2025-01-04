import os
from django.contrib.gis.utils import LayerMapping, LayerMapError
from .models import CulturalProperty

class CulturalPropertiesLoader:
    mapping = {
        'id': 'id',
        'name': 'name',
        'name_kana': 'name_kana',
        'name_gener': 'name_gener',
        'name_en': 'name_en',
        'category': 'category',
        'type': 'type',
        'place_name': 'place_name',
        'address': 'address',
        'latitude': 'latitude',
        'longitude': 'longitude',
        'url': 'url',
        'note': 'note',
        'geom': 'POINT',
    }
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'cultural_properties.shp'))

    @classmethod
    def run(cls, verbose=True):
        lm = LayerMapping(CulturalProperty, cls.path, cls.mapping, transform=False, encoding='utf-8')
        try:
            lm.save(strict=False, verbose=True)
        except LayerMapError as e:
            print(f"エラーが発生しました: {e}")