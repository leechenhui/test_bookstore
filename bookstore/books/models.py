from django.db import models
from tinymce.models import HTMLField
from db.base_model import BaseModel
from books.enums import *
from django.core.files.storage import FileSystemStorage
fs = FileSystemStorage(location='/root/test_bookstore/bookstore/collect_static')

# Create your models here.


# 自定义模型类管理器,添加额外方法
class BooksManager(models.Manager):
	# 根据商品类型的id查询商品信息
	def get_books_by_type(self, type_id, limit=None, sort='default'):
		if sort == 'new':
			order_by = ('-create_time',)
		elif sort == 'hot':
			order_by = ('-sales',)
		elif sort == 'price':
			order_by = ('price',)
		else:
			order_by = ('-pk',)

		# 根据书籍类型id和排序类型得到书籍列表
		books_li = self.filter(type_id=type_id).order_by(*order_by)

		# 获取排序好的书籍列表后进行切片
		if limit:
			books_li = books_li[:limit]
		return books_li

	# 根据书籍的id查询到书籍
	def get_books_by_id(self, books_id):
		try:
			book = self.get(id=books_id)
		except self.model.DoesNotExist:
			book = None
		return book


# 商品模型类
class Books(BaseModel):
	books_type_choices = ((k, v) for k, v in BOOKS_TYPE.items())
	status_choices = ((k, v) for k, v in STATUS_CHOICE.items())
	# 设置了choices的字段将构成一个二项元祖的可迭代对象,在后台中显示为下拉列表框,元组第二项目将作为value展示
	type_id = models.SmallIntegerField(default=PYTHON, choices=books_type_choices, verbose_name='商品种类')
	name = models.CharField(max_length=20, verbose_name='商品名称')
	desc = models.CharField(max_length=128, verbose_name='商品简介')
	price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
	unit = models.CharField(max_length=20, verbose_name='商品单位')
	stock = models.IntegerField(default=1, verbose_name='商品库存')
	sales = models.IntegerField(default=0, verbose_name='商品销量')
	detail = HTMLField(verbose_name='商品详情')
	image = models.ImageField(storage=fs,upload_to='books', verbose_name='商品图片')
	status = models.SmallIntegerField(default=ONLINE, choices=status_choices, verbose_name='商品状态')

	# 自定义模型类管理器
	objects = BooksManager()

	def __str__(self):
		return self.name

	class Meta:
		db_table = 's_books'
		verbose_name = '书籍'
		verbose_name_plural = verbose_name
