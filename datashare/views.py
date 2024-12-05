from typing import Any
from django.shortcuts import render
from django.views.generic import TemplateView
from datashare.forms import frmPublish

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

class frmPublishView(TemplateView):
    def __init__(self) -> None:
        self.params = {
            'title': '地理空間情報の共有サイト',
            'msg': 'これは投稿ページです。',
            'form': frmPublish(),
            'answer': None,
            'goto_index': 'datashare:index',
        }
    def get(self, request: Any) -> Any:
        return render(request, 'datashare/frmPublish.html', self.params)
    
    def post(self, request: Any) -> Any:
        person = request.POST['name']
        proj = request.POST['project']
        cont = request.POST['contents']
        self.params['answer'] = 'name=' + person + ', project=' + proj + ', contents=' + cont + '.'
        self.params['form'] = frmPublish(request.POST)
        return render(request, 'datashare/frmPublish.html', self.params)