from django.db import models
from db.base_model import BaseModel
from utils.get_hash import get_hash


# Create your models here.


# 自定义模型类管理器,添加额外方法
class PassportManager(models.Manager):
	# 添加一个账户信息
	def add_one_passport(self, username, password, email):
		passport = self.create(username=username, password=get_hash(password), email=email)
		return passport

	# 根据用户名和密码查找账户信息
	def get_one_passport(self, username, password):
		try:
			passport = self.get(username=username, password=get_hash(password))
		except self.model.DoesNotExist:
			passport = None
		return passport


# 定义用户模型类
class Passport(BaseModel):
	username = models.CharField(max_length=20, verbose_name='用户名称')
	password = models.CharField(max_length=40, verbose_name='用户密码')
	email = models.EmailField(verbose_name='用户邮箱')
	is_active = models.BooleanField(default=False, verbose_name='激活状态')

	# 重写模型类的管理器
	objects = PassportManager()

	def __str__(self):
		return self.username

	class Meta:
		db_table = 's_user_account'


# 定义地址模型管理器
class AddressManager(models.Manager):
	# 根据账户id找到默认的收货地址
	def get_default_address(self, passport_id):
		try:
			addr = self.get(passport_id=passport_id, is_default=True)
		except self.model.DoesNotExist:
			addr = None
		return addr

	# 添加一个新的收货地址
	def add_one_address(self, passport_id, recipient_name, recipient_addr, zip_code, recipient_phone):
		# 判断一个用户是否拥有默认收货信息
		addr = self.get_default_address(passport_id=passport_id)
		if addr:
			# 存在默认地址,False
			is_default = False
		else:
			# 不存在默认地址,True
			is_default = True

		# 新建一个收货地址信息
		addr = self.create(
			passport_id=passport_id,
			recipient_name=recipient_name,
			recipient_addr=recipient_addr,
			zip_code=zip_code,
			recipient_phone=recipient_phone,
			is_default=is_default
		)
		return addr


class Address(BaseModel):
	recipient_name = models.CharField(max_length=20, verbose_name='收件人')
	recipient_addr = models.CharField(max_length=256, verbose_name='收件地址')
	zip_code = models.CharField(max_length=6, verbose_name='邮政编码')
	recipient_phone = models.CharField(max_length=11, verbose_name='联系电话')
	is_default = models.BooleanField(default=False, verbose_name='是否默认')
	passport = models.ForeignKey('Passport', verbose_name='账户')

	objects = AddressManager()

	class Meta:
		db_table = 's_user_address'
