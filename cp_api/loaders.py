import os
from django.contrib.gis.utils import LayerMapping, LayerMapError
from .models import CulturalProperty

from django.db import transaction

class CulturalPropertiesLoader:
    mapping = {
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
    @transaction.atomic
    def run(cls, verbose=True):
        lm = LayerMapping(CulturalProperty, cls.path, cls.mapping, transform=False, encoding='utf-8')
        try:
            with transaction.atomic():
                lm.save(strict=False, verbose=True)
        except LayerMapError as e:
            transaction.set_rollback(True)  # トランザクションをロールバック
            print(f"エラーが発生しました: {e}")

class TaitoCulturalPropertiesLoader(CulturalPropertiesLoader):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'cultural_properties_taito.shp'))

class MinatoCulturalPropertiesLoader(CulturalPropertiesLoader):
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data', 'cultural_properties_minato.shp'))