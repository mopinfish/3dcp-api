from django.urls import path, include
from rest_framework import routers
from .views import (
    CulturalPropertyViewSet, 
    MovieViewSet, 
    TagViewSet,
    CSVImportPreviewView,
    CSVImportExecuteView,
)

router = routers.DefaultRouter()
router.register(r'cultural_property', CulturalPropertyViewSet)
router.register(r'movie', MovieViewSet)
router.register(r'tag', TagViewSet)

app_name = 'cp_api'

urlpatterns = [
    # ViewSetルーター
    path('', include(router.urls)),
    
    # CSVインポートAPI
    path('import/preview/', CSVImportPreviewView.as_view(), name='import-preview'),
    path('import/execute/', CSVImportExecuteView.as_view(), name='import-execute'),
]
