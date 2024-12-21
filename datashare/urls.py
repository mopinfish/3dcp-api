from django.urls import path
from . import views

app_name = 'datashare'

urlpatterns = [
    path('', views.index, name='index'),
    path('mypage/', views.mypage_funcView, name='mypage'),
    path('frmPublish/', views.frmPublishView.as_view(), name='frmPublish'),
]