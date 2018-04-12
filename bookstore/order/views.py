from django.shortcuts import render, redirect
from django.core.urlresolvers import reverse
from utils.decorators import login_required
from django.http import HttpResponse, JsonResponse
from users.models import Address
from books.models import Books
from order.models import OrderInfo, OrderGoods
from django_redis import get_redis_connection
from django.db import transaction
from datetime import datetime
import time
# Create your views here.


# 显示提交订单页面
@login_required
def order_place(request):
	# 接收数据,得到书籍id的列表
	books_ids = request.POST.getlist('books_ids')

	# 校验数据
	if not all(books_ids):
		# 跳转回购物车页面
		return redirect(reverse('cart:show'))

	# 用户收货地址
	passport_id = request.session.get('passport_id')
	addr = Address.objects.get_default_address(passport_id=passport_id)

	# 用户要购买商品的信息
	books_li = []

	# 商品的总数目和总金额
	total_count = 0
	total_price = 0

	conn = get_redis_connection('default')
	cart_key = 'cart_%d' % passport_id

	for id in books_ids:
		# 根据id获取商品的信息
		books = Books.objects.get_books_by_id(books_id=id)
		# 从redis中获取用户要购买的商品的数目
		count = conn.hget(cart_key, id)
		books.count = count
		# 计算商品的价格小计
		amount = int(count) * books.price
		books.amount = amount
		books_li.append(books)

		# 累计商品的总数量和总价格
		total_count += int(count)
		total_price += books.amount

	# 商品运费和实付款
	transit_price = 10
	total_pay = total_price + transit_price

	# 将书籍id拼接成字符串
	books_ids = ','.join(books_ids)
	context = {
		'addr': addr,
		'books_li': books_li,
		'total_count': total_count,
		'total_price': total_price,
		'transit_price': transit_price,
		'total_pay': total_pay,
		'books_ids': books_ids,
	}

	return render(request, 'order/place_order.html', context)


# 提交订单功能
# 需要向两张表中添加信息
# s_order_info:订单信息表,添加一条
# s_order_books:订单商品表,订单中买了几件商品,就添加几条记录

# 1.向订单表中添加一条信息
# 2.遍历向订单商品表中添加信息
	# 2.1添加订单商品信息之后,增加商品销量,减少库存
	# 2.2累计计算订单商品的总数目和总金额
# 3.更新订单商品的总数目和总金额
# 4.清除购物车对应信息


@transaction.atomic
def order_commit(request):
	# 判断用户是否登录
	if not request.session.has_key('islogin'):
		return JsonResponse({'res': 0, 'errmsg': '用户未登录'})

	# 接收数据
	addr_id = request.POST.get('addr_id')  # 地址id
	pay_method = request.POST.get('pay_method')  # 支付方式
	books_ids = request.POST.get('books_ids')  # 商品id的拼合字符串

	# 进行数据校验
	if not all([addr_id, pay_method, books_ids]):
		return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

	try:
		addr = Address.objects.get(id=addr_id)
	except Exception as e:
		return JsonResponse({'res': 2, 'errmsg': '地址信息错误'})

	if int(pay_method) not in OrderInfo.PAY_METHOD_ENUM.values():
		return JsonResponse({'res': 3, 'errmsg': '不支持的支付方式'})

	# 创建订单
	# 1获取用户id
	passport_id = request.session.get('passport_id')
	# 2构建订单id:20171029110830 + 用户id
	order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(passport_id)
	# 3设置运费
	transit_price = 10
	# 4订单商品总数和总金额
	total_count = 0
	total_price = 0

	# 创建一个保存点
	sid = transaction.savepoint()

	try:
		# 向订单信息表中添加一条记录
		order = OrderInfo.objects.create(
			order_id=order_id,
			passport_id=passport_id,
			addr_id=addr_id,
			total_count=total_count,
			total_price=total_price,
			transit_price=transit_price,
			pay_method=pay_method
		)

		# 向订单商品表中添加订)单商品的记录
		books_ids = books_ids.split(',')  # 将书籍id分割成列表
		conn = get_redis_connection('default')  # 链接redis
		cart_key = 'cart_%d' % passport_id  # 构建购物车id

		# 遍历获取用户购买的商品信息
		for id in books_ids:

			books = Books.objects.get_books_by_id(books_id=id)
			print('run 11')
			if books is None:
				transaction.savepoint_rollback(sid)
				return JsonResponse({'res': 4, 'errmsg': '商品信息错误'})

			# 获取用户购买的商品数目
			count = conn.hget(cart_key, id)

			# 判断商品的库存
			if int(count) > books.stock:
				transaction.savepoint_rollback(sid)
				return JsonResponse({'res': 5, 'errmsg': '商品库存不足'})

			# 创建一条订单商品记录
			OrderGoods.objects.create(
				order_id=order_id,
				books_id=id,
				count=int(count),
				price=books.price
			)

			# 增加商品的销量,减少商品库存
			books.sales += int(count)
			books.stock -= int(count)
			books.save()

			# 累计计算商品的总数和总金额
			total_count += int(count)
			total_price += int(count) * books.price

		# 更新订单的商品总数和总金额
		order.total_count = total_count
		order.total_price = total_price
		order.save()

	except Exception as e:
		transaction.savepoint_rollback(sid)
		return JsonResponse({'res': 7, 'errmsg': '服务器错误'})

	# 清除购物车对应记录
	conn.hdel(cart_key, *books_ids)

	# 事务提交
	transaction.savepoint_commit(sid)
	# 返回应答
	return JsonResponse({'res': 6})