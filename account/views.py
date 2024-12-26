from django.shortcuts import render
from account.forms import LoginForm
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

# Create your views here.
class TopView(LoginRequiredMixin, TemplateView):
    template_name = 'account/top.html'

class MyLoginView(LoginView):
    form_class = LoginForm
    template_name = 'account/login.html'

class MyLogoutView(LogoutView):
    template_name = 'account/logout.html'
