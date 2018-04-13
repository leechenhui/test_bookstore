from django.core.paginator import Paginator
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from books.models import Books
from books.enums import *
from django.views.decorators.cache import cache_page
from django_redis import get_redis_connection


# Create your views here.


# 显示首页
# 使用redis缓存首页页面
# @cache_page(60*15)
def index(request):
	# 查询每个种类的3个新品和4个销量最好的商品
	python_new = Books.objects.get_books_by_type(PYTHON, 3, sort='new')
	python_hot = Books.objects.get_books_by_type(PYTHON, 4, sort='hot')
	javascript_new = Books.objects.get_books_by_type(JAVASCRIPT, 3, sort='new')
	javascript_hot = Books.objects.get_books_by_type(JAVASCRIPT, 4, sort='hot')
	algorithms_new = Books.objects.get_books_by_type(ALGORITHMS, 3, sort='new')
	algorithms_hot = Books.objects.get_books_by_type(ALGORITHMS, 4, sort='hot')
	machinelearning_new = Books.objects.get_books_by_type(MACHINELEARNING, 3, sort='new')
	machinelearning_hot = Books.objects.get_books_by_type(MACHINELEARNING, 4, sort='hot')
	operatingsystem_new = Books.objects.get_books_by_type(OPERATINGSYSTEM, 3, sort='new')
	operatingsystem_hot = Books.objects.get_books_by_type(OPERATINGSYSTEM, 4, sort='hot')
	database_new = Books.objects.get_books_by_type(DATABASE, 3, sort='new')
	database_hot = Books.objects.get_books_by_type(DATABASE, 4, sort='hot')

	# 定义模板上下文
	context = {
		'python_new': python_new,
		'python_hot': python_hot,
		'javascript_new': javascript_new,
		'javascript_hot': javascript_hot,
		'algorithms_new': algorithms_new,
		'algorithms_hot': algorithms_hot,
		'machinelearning_new': machinelearning_new,
		'machinelearning_hot': machinelearning_hot,
		'operatingsystem_new': operatingsystem_new,
		'operatingsystem_hot': operatingsystem_hot,
		'database_new': database_new,
		'database_hot': database_hot,
	}
	return render(request, 'books/index.html', context)


# 商品详情页面
def detail(request, book_id):
	# 根据书籍id找到书籍
	book = Books.objects.get_books_by_id(books_id=book_id)
	# 如果书籍不存在就回到首页
	if book is None:
		return redirect(reverse('books:index'))

	# 如果书籍存在根据书籍的类型id找到那一类型的所有数,并且获取两本最新上架的书
	books_li = Books.objects.get_books_by_type(type_id=book.type_id, limit=2, sort='new')

	if request.session.has_key('islogin'):
		# 用户已经登录,记录浏览记录
		con = get_redis_connection('default')
		key = 'history_%d' % request.session.get('passport_id')
		# 先从redis列表中移除book.id
		con.lrem(key, 0, book.id)
		con.lpush(key, book.id)
		# 保存用户最近浏览的5个商品
		con.ltrim(key, 0, 4)

	# 将这本数和新书列表渲染到书籍详情页面
	context = {'book': book, 'books_li': books_li}
	return render(request, 'books/detail.html', context)


# 商品列表页面
def list(request, type_id, page):
	# 获取排序方式(默认/价格/热度)
	sort = request.GET.get('sort', 'default')

	# 判断书籍类型是否合法
	if int(type_id) not in BOOKS_TYPE.keys():
		return redirect(reverse('books:index'))

	# 根据书籍类型id获取和排序方式获取书籍列表
	books_li = Books.objects.get_books_by_type(type_id=type_id, sort=sort)

	# 根据获得的书籍列表生成分页实例对象,每页有1条数据
	paginator = Paginator(books_li, 1)
	# 获取分页后的总页数
	num_pages = paginator.num_pages

	# 判断当前页码数(如果为空或者大于总页数,那就返回第一页)
	if page == '' or int(page) > num_pages:
		page = 1
	else:
		page = int(page)

	# 获取指定页码数的页面对象
	books_li = paginator.page(page)
	print(books_li)
	print(type(books_li))
	for book in books_li:
		print(type(book))
		print(book.price)

	# 总页数小于5,显示所有页码
	# range函数计数范围不包括stop
	if num_pages < 5:
		# [1,...,num_pages]
		pages = range(1, num_pages + 1)
	# 当前页是前3页,显示前5页
	elif page <= 3:
		pages = range(1, 6)
	# 当前页是后3页,显示后5页
	elif num_pages - page <= 2:
		pages = range(num_pages - 4, num_pages + 1)
	# 其他情况显示前2页,当前页,后2页
	else:
		pages = range(page - 2, page + 3)

	# 获取新品推荐书籍列表
	books_new = Books.objects.get_books_by_type(type_id=type_id, limit=2, sort='new')

	# 获取书籍类名
	type_title = BOOKS_TYPE[int(type_id)]

	# 定义上下文
	context = {
		'books_li': books_li,
		'books_new': books_new,
		'type_id': type_id,
		'sort': sort,
		'type_title': type_title,
		'pages': pages,
	}

	return render(request, 'books/list.html', context)
