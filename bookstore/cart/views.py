from django.shortcuts import render
from django.http import JsonResponse
from books.models import Books
from utils.decorators import login_required
from django_redis import get_redis_connection


# Create your views here.


def cart_add(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 接收数据
	books_id = request.POST.get('books_id')
	books_count = request.POST.get('books_count')

	# 进行数据校验
	if not all([books_id, books_count]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	# 校验商品id是否存在
	books = Books.objects.get_books_by_id(books_id=books_id)
	if books is None:
		return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

	# 校验商品数量是否合法
	try:
		count = int(books_count)
	except Exception as e:
		return JsonResponse({'res': 3, 'errmsg': '商品数量必须为数字'})

	# 如果校验全部通过,就把商品添加到购物车
	# 每个用户的购物车信息用一条hash数据保存
	# cart_用户id:商品id 商品数量

	# 链接redis数据库
	conn = get_redis_connection('default')
	# 设置购物车id,也就是hash的key.
	cart_key = 'cart_%d' % request.session.get('passport_id')

	# 根据购物车id和商品id去获取商品数量
	res = conn.hget(cart_key, books_id)
	# 如果该用户的购物车中没有该商品的数据,就添加该商品数量信息
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

	return JsonResponse({'res': 5})


# 登录后将商品数量信息渲染到购物车中
def cart_count(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0})

	conn = get_redis_connection('default')
	cart_key = 'cart_%d' % request.session.get('passport_id')

	# 获取购物车中所有商品的数量信息,并且进行累加
	res = 0
	res_list = conn.hvals(cart_key)
	for i in res_list:
		res += int(i)

	return JsonResponse({'res': res})


# 显示用户购物车页面的函数
@login_required
def cart_show(request):
	passport_id = request.session.get('passport_id')
	conn = get_redis_connection('default')
	cart_key = 'cart_%d' % passport_id
	# 获取用户购物车里的所有记录,包括书名和书籍数量
	res_dict = conn.hgetall(cart_key)
	# hgetall返回hash表的所有字段和值

	books_li = []
	total_count = 0
	total_price = 0

	# 遍历获取商品所有的数据
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
		'books_li': books_li,
		'total_count': total_count,
		'total_price': total_price,
	}

	return render(request, 'cart/cart.html', context)


def cart_del(request):
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '请先登录'})

	# 判断数据是否完整
	books_id = request.POST.get('books_id')
	if not all([books_id]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	# 判断商品是否存在
	books = Books.objects.get_books_by_id(books_id)
	if books is None:
		return JsonResponse({'res': 2, 'errmsg': '商品不存在'})

	# 删除购物车中该商品的信息
	conn = get_redis_connection('default')
	cart_key = 'cart_%d' % request.session.get('passport_id')
	conn.hdel(cart_key, books_id)
	# 删除hash对象中某个key的指定字段

	return JsonResponse({'res': 3})



