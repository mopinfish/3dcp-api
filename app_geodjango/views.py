from django.shortcuts import render
from .models import city_border, stations
from .forms import frmStation
from django.views.generic import TemplateView

# Create your views here.
class StationView(TemplateView):
    template_name = 'app_geodjango/station.html'

    def __init__(self):
        self.params = {
            'title': 'Station',
            'message': 'This is a station page.',
            'form': frmStation(),
            'latitude': 35.681236,
            'longitude': 139.767125,
            'station_name': 'Tokyo Station',
            'city_name': 'Tokyo',
        }

    def get(self, request):
        self.params['stations'] = stations.objects.filter(pref_cd=13)
        print('=-============')
        print(len(self.params['stations']))
        print('=-============')
        return render(request, self.template_name, self.params)
    
    def post(self, request):
        station_cd = request.POST['selected_station']


