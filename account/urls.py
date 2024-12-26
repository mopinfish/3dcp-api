from django.urls import path
from account.views import TopView, MyLoginView, MyLogoutView

app_name = 'account'

urlpatterns = [
    path('', TopView.as_view(), name='top'),
    path('login/', MyLoginView.as_view(), name='login'),
    path('logout/', MyLogoutView.as_view(), name='logout'),
]