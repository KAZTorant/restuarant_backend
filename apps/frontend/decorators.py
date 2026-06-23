from functools import wraps

from django.shortcuts import redirect


def pin_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('authenticated'):
            return redirect('frontend:login')
        return view_func(request, *args, **kwargs)
    return wrapper
