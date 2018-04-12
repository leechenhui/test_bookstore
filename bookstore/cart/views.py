from django.shortcuts import render
from django.http import JsonResponse
from books.models import Books
from utils.decorators import login_required
from django_redis import get_redis_connection


# Create your views here.


# 向购物车中添加数据
def cart_add(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 接收数据(书籍id,书籍数量)
	books_id = request.POST.get('books_id')
	books_count = request.POST.get('books_count')

	# 进行数据校验(数据是否完整)
	if not all([books_id, books_count]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	# 进行数据校验(书籍id是否存在)
	books = Books.objects.get_books_by_id(books_id=books_id)
	if books is None:
		return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

	# 进行数据校验(书籍数量是否合法)
	try:
		count = int(books_count)
	except Exception as e:
		return JsonResponse({'res': 3, 'errmsg': '商品数量必须为数字'})

	# 如果校验全部通过,就把商品添加到购物车
	# 每个用户的购物车信息用一条hash数据保存
	# cart_用户id:商品id 商品数量

	# 链接redis数据库
	conn = get_redis_connection('default')
	# 设置登录用户的购物车id(也就是hash的key).
	cart_key = 'cart_%d' % request.session.get('passport_id')

	# 根据购物车id和商品id去获取商品数量
	res = conn.hget(cart_key, books_id)
	# 如果该用户的购物车中没有该商品的数量信息,就添加该商品数量信息
	if res is None:
		res = count
	else:
		# 如果该用户的购物车中有该商品的数据,就累计商品数量
		res = int(res) + count

	# 判断商品库存是否足够
	if res > books.stock:
		return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
	else:
		conn.hset(cart_key, books_id, res)

	# 数据判断更新完成后,返回5
	return JsonResponse({'res': 5})


# 登录后将商品数量信息渲染到购物车页面中
def cart_count(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 链接redis数据库
	conn = get_redis_connection('default')
	# 设置该用户的购物车id
	cart_key = 'cart_%d' % request.session.get('passport_id')

	# 根据购物车id获取车中所有商品的数量信息,进行累加
	res = 0
	res_list = conn.hvals(cart_key)
	for i in res_list:
		res += int(i)

	# 将书籍总数通过json返回
	return JsonResponse({'res': res})


# 显示用户购物车页面
@login_required
def cart_show(request):
	# 获取用户的id
	passport_id = request.session.get('passport_id')
	# 链接redis
	conn = get_redis_connection('default')
	# 根据用户id构建购物车的id
	cart_key = 'cart_%d' % passport_id
	# 获取用户购物车里的所有记录,包括书名和书籍数量
	res_dict = conn.hgetall(cart_key)
	# hgetall返回hash表的所有字段和值

	books_li = []
	total_count = 0
	total_price = 0

	# 遍历获取商品所有的数据
	# res_dict是个列表怎么当做字典使用的呢?
	for id, count in res_dict.items():
		# 根据id获取对应商品
		books = Books.objects.get_books_by_id(books_id=id)
		# 保存商品的数目
		books.count = count
		# 保存商品的价格小计
		books.amount = int(count) * books.price
		# 将商品存入空列表中
		books_li.append(books)

		total_count += int(count)
		total_price += int(count) * books.price

	context = {
		# 购物车的商品列表
		'books_li': books_li,
		# 书籍的总数量
		'total_count': total_count,
		# 书籍的价格总计
		'total_price': total_price,
	}

	return render(request, 'cart/cart.html', context)


# 购物车中删除商品的功能
def cart_del(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 接收数据
	books_id = request.POST.get('books_id')

	# 判断数据是否完整
	if not all([books_id]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	# 判断商品是否存在
	books = Books.objects.get_books_by_id(books_id)
	if books is None:
		return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

	# 链接redis数据库
	conn = get_redis_connection('default')
	# 构建用户的购物车id
	cart_key = 'cart_%d' % request.session.get('passport_id')
	# 删除指定购物车指定商品
	conn.hdel(cart_key, books_id)

	# 删除成功返回信息3
	return JsonResponse({'res': 3})


# 前端传来的参数:商品id:books_id,更新数目:books_count
def cart_update(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 接收获取前端传来的参数
	books_id = request.POST.get('books_id')
	books_count = request.POST.get('books_count')

	# 对数据进行校验
	if not all([books_id, books_count]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	books = Books.objects.get_books_by_id(books_id=books_id)
	if books is None:
		return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

	try:
		books_count = int(books_count)
	except Exception as e:
		return JsonResponse({'res': 3, 'errmsg': '商品数目必须为数字'})

	# 链接redis,根据账户id获取购物车id
	conn = get_redis_connection('default')
	cart_key = 'cart_%d' % request.session.get('passport_id')

	# 判断商品库存
	if books_count > books.stock:
		return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

	# 更新该购物车该商品的数量信息
	conn.hset(cart_key, books_id, books_count)

	return JsonResponse({'res': 5})