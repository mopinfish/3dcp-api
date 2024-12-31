from django import forms
from .models import stations

class frmStation(forms.Form):
    selected_station = forms.ChoiceField(choices=stations.objects.all().values_list('station_cd', 'station_na'), widget=forms.Select(), required=True)