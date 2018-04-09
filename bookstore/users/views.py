import re
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import Passport, Address
from django.core.urlresolvers import reverse
from utils.get_hash import get_hash
from utils.decorators import login_required


# Create your views here.

# 调用账户注册页面
def register(request):
	return render(request, 'users/register.html')


# 进行用户注册处理
def register_handle(request):
	# 接收表单提交数据
	username = request.POST.get('user_name')
	password = request.POST.get('pwd')
	email = request.POST.get('email')

	# 进行数据校验
	if not all([username, password, email]):
		return render(request, 'users/register.html', {'errmsg': '参数不能为空.'})

	# 校验邮箱
	if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
		return render(request, 'users/register.html', {'errmsg': '邮箱不合法.'})

	passport = Passport.objects.add_one_passport(username=username, password=password, email=email)
	passport.save()
	return redirect(reverse('books:index'))


# 显示登录页面
def login(request):
	username = ''
	checked = ''
	context = {
		'username': username,
		'checked': checked,
	}
	return render(request, 'users/login.html', context)


def login_check(request):
	# 获取表单提交的数据
	username = request.POST.get('username')
	password = request.POST.get('password')
	remember = request.POST.get('remember')

	# 根据用户名和密码查找账户信息
	passport = Passport.objects.get_one_passport(username=username, password=password)
	# 如果用户名和密码都正确的话
	if passport:
		response = {
			'next_url': reverse('books:index'),
			'code': 200,
		}
		jres = JsonResponse(response)

		if remember == 'true':
			jres.set_cookie('username', username, max_age=7 * 24 * 3600)
		else:
			jres.delete_cookie('username')

		# 记住用户登录状态
		request.session['islogin'] = True
		request.session['username'] = username
		request.session['passport_id'] = passport.id
		return jres
	else:
		return JsonResponse({'code': 500})


def logout(request):
	request.session.flush()
	return redirect(reverse('books:index'))


# 调取用户信息页面的函数
@login_required
def user(request):
	# 获取账户id
	passport_id = request.session.get('passport_id')
	# 根据账户id获取账户的默认地址信息
	addr = Address.objects.get_default_address(passport_id=passport_id)

	books_li = []

	context = {
		'addr': addr,
		'page': 'user',
		'books_li': books_li,
	}
	return render(request, 'users/user_center_info.html', context)