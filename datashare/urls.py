from django.urls import path
from . import views

app_name = 'datashare'
urlpatterns = [
    path('', views.index, name='index'),
]
