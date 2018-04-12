from django.conf.urls import url
from . import views

urlpatterns=[
	url(r'^add/$',views.cart_add,name='add'),
	url(r'^count/$',views.cart_count,name='count'),
	url(r'^$',views.cart_show,name='show'),
	url(r'^del/$',views.cart_del,name='delete'),
	url(r'^update/$',views.cart_update,name='update'),
]
