from typing import Any
from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from datashare.forms import frmPublish
from .models import pub_message
from .forms import frmModelPublish, LoginForm


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

class mypage_dbView(LoginRequiredMixin, TemplateView):
    template_name = 'datashare/mypage_db.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pub_message_list'] = pub_message.objects.all().order_by('id')
        context['title'] = '地理空間情報の共有サイト'
        context['msg'] = 'これはマイページ（DB接続）です。'
        context['goto_index'] = 'datashare:index'
        context['goto_publish_db'] = 'datashare:publish_db'
        context['goto_logout'] = 'datashare:logout'
        context['user'] = self.request.user
        user_id = self.request.user.id
        sql = 'SELECT * FROM datashare_pub_message'
        sql += ' WHERE project_id in'
        sql += ' (SELECT distinct group_id as project_id FROM auth_user_groups'
        sql += ' WHERE user_id = ' + str(user_id) + ')'
        context['pub_message_list'] = pub_message.objects.raw(sql)
        sql = 'SELECT * FROM auth_group'
        sql += ' WHERE id in (SELECT distinct group_id FROM auth_user_groups '
        sql += ' WHERE user_id = ' + str(user_id) + ')'
        my_project = pub_message.objects.raw(sql)
        context['my_project'] = my_project

        return context

def publish_byModelfrmView(request):
    params = {
        'title': '地理空間情報の共有サイト',
        'msg': 'これは投稿ページ（モデルフォーム）です。',
        'form': frmModelPublish(),
        'goto_mypage_db': 'datashare:mypage_db',
    }
    if (request.method == 'POST'):
        form = frmModelPublish(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('datashare:mypage_db')
        else:
            form = frmModelPublish()

    return render(request, 'datashare/publish_db.html', params)

def edit(request, num):
    obj = pub_message.objects.get(id=num)
    if (request.method == 'POST'):
        if 'btn_update' in request.POST:
            form = frmModelPublish(request.POST, instance=obj)
            form.save()
            return redirect('datashare:mypage_db')
        elif 'btn_delete' in request.POST:
            obj.delete()
            return redirect('datashare:mypage_db')
        elif 'btn_back' in request.POST:
            return redirect('datashare:mypage_db')
    params = {
        'title': '地理空間情報の共有サイト',
        'msg': 'これは地理空間情報の編集ページです。',
        'id': num,
        'form': frmModelPublish(instance=obj),
        'goto_mypage_db': 'datashare:mypage_db',
    }
    return render(request, 'datashare/edit.html', params)


class MyLoginView(LoginView):
    form_class = LoginForm
    template_name = 'datashare/login.html'

class MyLogoutView(LogoutView):
    template_name = 'datashare/logout.html'