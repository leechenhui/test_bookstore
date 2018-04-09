from django.core.urlresolvers import reverse
from django.shortcuts import redirect


def login_required(view_func):
	def wrapper(request,*view_args,**view_kwargs):
		if request.session.has_key('islogin'):
			return view_func(request,*view_args,**view_kwargs)
		else:
			return redirect(reverse('user:login'))
	return wrapper