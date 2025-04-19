from django.urls import path, include
from rest_framework import routers
from .views import CulturalPropertyViewSet, MovieViewSet, TagViewSet 

router = routers.DefaultRouter()
router.register(r'cultural_property', CulturalPropertyViewSet)
router.register(r'movie', MovieViewSet)
router.register(r'tag', TagViewSet)

app_name = 'cp_api'

urlpatterns = [
    path('', include(router.urls)),
]