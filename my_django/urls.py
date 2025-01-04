"""
URL configuration for my_django project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import IndexView
from open3d_map.views import CulturalPropertyViewSet, MovieViewSet
from rest_framework import routers

# Django REST framework API router
router = routers.SimpleRouter()
router.register(r'movies', MovieViewSet)
router.register(r'cultural_properties', CulturalPropertyViewSet)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', admin.site.urls),
    path('datashare/', include('datashare.urls')),
    path('account/', include('account.urls')),
    path('app_geodjango/', include('app_geodjango.urls')),
    path('open3d_map/', include('open3d_map.urls')),
    # Django REST framework API
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v1/', include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)