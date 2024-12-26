from django.urls import path
from . import views

app_name = 'datashare'

urlpatterns = [
    path('', views.index, name='index'),
    path('mypage/', views.mypage_funcView, name='mypage'),
    path('frmPublish/', views.frmPublishView.as_view(), name='frmPublish'),
    path('mypage_db/', views.mypage_dbView.as_view(), name='mypage_db'),
    path('publish_db', views.publish_byModelfrmView, name='publish_db'),
    path('edit/<int:num>', views.edit, name='edit'),
    path('login/', views.MyLoginView.as_view(), name='login'),
    path('logout/', views.MyLogoutView.as_view(), name='logout'),
]