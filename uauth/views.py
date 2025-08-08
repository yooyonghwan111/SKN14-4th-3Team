from django.shortcuts import render
from django.contrib import auth
from django.shortcuts import redirect
from django.db import transaction
from django.contrib.auth.models import User
from django.http import JsonResponse

from .models import UserForm


def logout(request):
  auth.logout(request) # django.contrib.auth 로그아웃 처리
  return redirect('main:index')

# @transaction.atomic
def signup(request):
  """
  @transaction.atomic: 함수 전체를 트랜잭션 범위로 지정하고, 문제없이 함수가 종료/반환되면 commit, 아니면 rollback처리
  with transaction.atomic() 블럭 안에서 트랜잭션 코드 작성도 가능
  """
  if request.method == 'POST':
    form = UserForm(request.POST, request.FILES) 
    if form.is_valid():
      print(f'{form.cleaned_data=}')
      
      # User 모델 저장
      user = form.save(commit=True)
      print(f'{user=}')

      # 로그인처리
      username = form.cleaned_data['username']
      password = form.cleaned_data['password1']
      authenticated_user = auth.authenticate(username=username, password=password) # 인증
      if authenticated_user is not None:
        auth.login(request, authenticated_user) # 로그인처리
      return redirect('main:index')
  else: 
    form = UserForm()

  return render(request, 'uauth/signup.html', {'form': form})


def check_username(request):
  """
  회원가입시 username 중복여부를 검사하는 ajax처리 뷰함수
  """
  username = request.GET.get('username')
  # 사용가능여부 
  available =  User.objects.filter(username=username).exists() == False
  print(f"{username=}, {available=}")

  return JsonResponse({'available': available})