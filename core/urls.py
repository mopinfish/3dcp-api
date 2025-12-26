from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import IndexView
from cp_api.views import CulturalPropertyViewSet, MovieViewSet, TagViewSet
from rest_framework import routers

# Django REST framework API router
router = routers.SimpleRouter()
router.register(r'movies', MovieViewSet)
router.register(r'cultural_properties', CulturalPropertyViewSet)
router.register(r'tags', TagViewSet)

urlpatterns = [
    path('', IndexView.as_view(), name='index'),
    path('admin/', admin.site.urls),
    
    # Django Template用 (accountアプリ)
    path('account/', include('account.urls', namespace='account')),
    
    # REST API用
    path('cp_api/', include('cp_api.urls')),
    path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
    path('api/v1/', include(router.urls)),
    
    # 認証API (namespace を auth に変更)
    path('api/v1/auth/', include(('account.urls', 'account'), namespace='auth')),
]

# メディアファイルの配信（開発環境・本番環境両方）
# 本番環境ではNginx等で配信するのが理想だが、Fly.ioではDjangoで直接配信
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)