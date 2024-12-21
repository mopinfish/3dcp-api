from typing import Any
from django.shortcuts import render
from django.views.generic import TemplateView
from datashare.forms import frmPublish
from .models import pub_message

# Create your views here.
def index(request):
    params = {
        'title': '地理空間情報の共有サイト',
        'msg': 'これはトップページです。',
        'goto_mypage': 'datashare:mypage',
        'goto_mypage_db': 'datashare:mypage_db',
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

class mypage_dbView(TemplateView):
    template_name = 'datashare/mypage_db.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pub_message_list'] = pub_message.objects.all().order_by('id')
        context['title'] = '地理空間情報の共有サイト'
        context['msg'] = 'これはマイページ（DB接続）です。'
        context['goto_index'] = 'datashare:index'
        return context