from django.urls import path
from .views import StationView

app_name = 'app_geodjango'

urlpatterns = [
    path('station/', StationView.as_view(), name='station'),
]