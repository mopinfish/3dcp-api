from django.shortcuts import render

# Create your views here.
def index(request):
    params = {
        'title': '地理空間情報の共有サイト',
        'msg': 'これはトップページです。',
        'goto_mypage': 'datashare:mypage',
    }
    return render(request, 'datashare/index.html', params)

def mypage_funcView(request):
    params = {
        'title': '地理空間情報の共有サイト',
        'msg': 'これはマイページです。',
        'goto_index': 'datashare:index',
    }
    return render(request, 'datashare/mypage.html', params)