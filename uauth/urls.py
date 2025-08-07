from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'uauth'

urlpatterns = [
    # GET: 로그인 폼페이지 응답
    # POST: 사용자인증정보 처리
    path('login/', auth_views.LoginView.as_view(template_name='uauth/login.html'), name='login'),
    path('logout/', views.logout, name='logout'),
    
    path('signup/', views.signup, name='signup'),

    path('check_username/', views.check_username, name='check_username'),
]