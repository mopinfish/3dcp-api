from django.shortcuts import render

# Create your views here.
def index(request):
    params = {
        'title': '地理空間情報のサイト',
        'msg': 'これはトップページです。',
    }
    return render(request, 'datashare/index.html', params)