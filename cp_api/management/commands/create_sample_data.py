from django.core.management.base import BaseCommand
from django.contrib.gis.geos import Point
from faker import Faker
from cp_api.models import CulturalProperty, Movie
import random

class Command(BaseCommand):
    help = 'Creates sample data for Movie model'

    def handle(self, *args, **kwargs):
        fake = Faker()
        
        # まず、CulturalPropertyのサンプルデータを作成
        for _ in range(10):  # 10個のCulturalPropertyを作成
            cultural_property = CulturalProperty.objects.create(
                name=fake.company(),
                name_kana=fake.company_suffix(),
                name_gener=fake.company_suffix(),
                name_en=fake.company(),
                category=random.choice(['建造物', '美術品', '記念物']),
                type=random.choice(['国宝', '重要文化財', '史跡']),
                place_name=fake.city(),
                address=fake.address(),
                latitude=fake.latitude(),
                longitude=fake.longitude(),
                url=fake.url(),
                note=fake.text(max_nb_chars=200),
                geom=Point(float(fake.longitude()), float(fake.latitude()), srid=6668)
            )
            
            # 各CulturalPropertyに対して1〜3個のMovieを作成
            for _ in range(random.randint(1, 3)):
                Movie.objects.create(
                    cultural_property=cultural_property,
                    url=fake.url(),
                    title=fake.sentence(nb_words=6),
                    note=fake.text(max_nb_chars=200)
                )
        
        self.stdout.write(self.style.SUCCESS('Successfully created sample data'))
