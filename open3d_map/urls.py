from django.urls import path, include
from rest_framework import routers
from .views import CulturalPropertyViewSet, MovieViewSet 

router = routers.DefaultRouter()
router.register(r'cultural_property', CulturalPropertyViewSet)
router.register(r'movie', MovieViewSet)

app_name = 'open3d_map'

urlpatterns = [
    path('', include(router.urls)),
]