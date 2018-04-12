import re
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from .models import Passport, Address
from django.core.urlresolvers import reverse
from utils.get_hash import get_hash
from utils.decorators import login_required
from order.models import OrderInfo, OrderGoods
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from itsdangerous import SignatureExpired
# itsdangerous是一个产生token的库
from bookstore import settings
from django.core.mail import send_mail
from django_redis import get_redis_connection
from books.models import Books


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

	# 校验数据是否齐全
	if not all([username, password, email]):
		return render(request, 'users/register.html', {'errmsg': '参数不能为空.'})

	# 校验邮箱是否合法
	if not re.match(r'^[a-z0-9][\w\.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
		return render(request, 'users/register.html', {'errmsg': '邮箱不合法.'})

	p = Passport.objects.check_passport(username=username)

	if p:
		return render(request, 'users/register.html', {'errmsg': '用户名已存在!'})

	# 进行业务处理:注册,向账户系统中添加账户
	passport = Passport.objects.add_one_passport(username=username, password=password, email=email)
	# passport.save()

	serializer = Serializer(settings.SECRET_KEY, 3600)
	token = serializer.dumps({'confirm': passport.id})
	token = token.decode()

	send_mail('尚硅谷书城用户激活', '', settings.EMAIL_FROM, [email],
			  html_message='<a href="http://127.0.0.1:8000/user/active/%s/">http://127.0.0.1:8000/user/active/</a>' % token)

	return redirect(reverse('books:index'))


# 用户账户激活
def register_active(request,token):
	serializer = Serializer(settings.SECRET_KEY,3600)
	try:
		info = serializer.loads(token)
		passport_id = info['confirm']
		passport = Passport.objects.get(id=passport_id)
		passport.is_active = True
		passport.save()
		return redirect(reverse('user:login'))
	except SignatureExpired:
		return HttpResponse('激活链接已经过期')


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
	verifycode = request.POST.get('verifycode')

	# 数据校验
	if not all([username, password, remember, verifycode]):
		return JsonResponse({'code': 0, 'errmsg': '数据不完整'})

	if verifycode.upper() != request.session['verifycode']:
		return JsonResponse({'code': 1, 'errmsg': '验证码错误'})

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

	# 获取用户的最近浏览信息
	con = get_redis_connection('default')
	key = 'history_%d' % passport_id
	# 取出用户最近浏览的5个商品的id
	history_li = con.lrange(key,0,4)
	# 将这五本书遍历取出放入列表,渲染到前端
	books_li = []
	for id in history_li:
		books = Books.objects.get_books_by_id(books_id=id)
		books_li.append(books)

	context = {
		'addr': addr,
		'page': 'user',
		'books_li': books_li,
	}
	return render(request, 'users/user_center_info.html', context)


# 用户中心-地址页
@login_required
def address(request):
	# 获取登录用户的id
	passport_id = request.session.get('passport_id')

	if request.method == 'GET':
		addr = Address.objects.get_default_address(passport_id=passport_id)
		return render(request, 'users/user_center_site.html', {'addr': addr, 'page': address})
	else:
		# 添加收货地址
		# 1.接收数据
		recipient_name = request.POST.get('username')
		recipient_addr = request.POST.get('addr')
		zip_code = request.POST.get('zip_code')
		recipient_phone = request.POST.get('phone')

		# 2.进行校验
		if not all([recipient_name, recipient_addr, zip_code, recipient_phone]):
			return render(request, 'users/user_center_site.html', {'errmsg': '参数不能为空'})

		# 3.添加收货地址
		Address.objects.add_one_address(
			passport_id=passport_id,
			recipient_name=recipient_name,
			recipient_addr=recipient_addr,
			zip_code=zip_code,
			recipient_phone=recipient_phone
		)

		# 4.返回应答
		return redirect(reverse('user:address'))


@login_required
def order(request):
	# 查询用户的id
	passport_id = request.session.get('passport_id')

	# 获取订单信息
	order_li = OrderInfo.objects.filter(passport_id=passport_id)

	# 遍历订单获取商品信息
	for order in order_li:
		# 根据订单id查询订单商品信息
		order_id = order.order_id
		order_books_li = OrderGoods.objects.filter(order_id=order_id)

		# 计算商品的小计
		for order_books in order_books_li:
			count = order_books.count
			price = order_books.price
			amount = count * price
			order_books.amount = amount

		# 给order对象动态增加一个属性order_books_li,保存订单中商品的信息
		order.order_books_li = order_books_li

	context = {
		'order_li': order_li,
		'page': 'order'
	}

	return render(request, 'users/user_center_order.html', context)


def verifycode(request):
	# 引入绘图模块
	from PIL import Image, ImageDraw, ImageFont
	# 引入随机模块
	import random

	# 定义变量,用于画面的背景色,宽,高
	bgcolor = (random.randrange(20, 100), random.randrange(20, 100), 255)
	width = 100
	height = 25

	# 创建画面对象(也就是最终显示的验证码图片)
	im = Image.new('RGB', (width, height), bgcolor)

	# 创建画笔对象,该画笔对象将在im画面对象上进行绘制
	draw = ImageDraw.Draw(im)

	# 调用画笔的point()函数绘制噪点
	for i in range(0, 100):
		# 噪点的坐标
		xy = (random.randrange(0, width), random.randrange(0, height))
		# 噪点的颜色
		fill = (random.randrange(0, 255), 255, random.randrange(0, 255))
		# 绘制
		draw.point(xy, fill=fill)

	# 定义验证码的备选值
	str1 = 'ABCD123EFGHIJK456LMNOPQRS789TUVWXYZ0'

	# 随机选取4个值作为验证码
	rand_str = ''
	for i in range(0, 4):
		rand_str += str1[random.randrange(0, len(str1))]

	# 构造字体对象
	font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 15)

	# 构造字体颜色
	fontcolor = (255, random.randrange(0, 255), random.randrange(0, 255))

	# 绘制4个字
	# 参数:字符串左上角坐标,要写入的字符串,
	draw.text((5, 2), rand_str[0], font=font, fill=fontcolor)
	draw.text((25, 2), rand_str[1], font=font, fill=fontcolor)
	draw.text((50, 2), rand_str[2], font=font, fill=fontcolor)
	draw.text((75, 2), rand_str[3], font=font, fill=fontcolor)

	# 释放画笔
	del draw

	# 将生产的验证码字符串存入session,用于做进一步的验证
	request.session['verifycode'] = rand_str

	# 内存文件操作
	import io
	# 实例一个读写二进制文件的对象
	buf = io.BytesIO()
	# 将图片保存在内存中,文件类型为png
	im.save(buf, 'png')
	# 将内存中的图片数据返回给客户端,MIME类型为图片png
	return HttpResponse(buf.getvalue(), 'image/png')
