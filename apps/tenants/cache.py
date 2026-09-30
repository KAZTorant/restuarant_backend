from functools import wraps

from django.utils.cache import patch_cache_control
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers


def tenant_cache_page(timeout):
    """Cache a GET response per restaurant.

    ``cache_page`` keys only the URL. These endpoints are shared across
    tenants (``/api/tables/rooms/``, ``/api/meals/groups/``) and the tenant
    is carried on ``X-Restaurant-Slug`` or the session. Without a tenant
    prefix, the first restaurant's halls, tables and menu are reused for
    every later login for ``CACHE_TIME_IN_SECONDS``.
    """

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            restaurant = getattr(request, "restaurant", None)
            if restaurant is None:
                response = view_func(request, *args, **kwargs)
                patch_cache_control(
                    response,
                    no_cache=True,
                    no_store=True,
                    must_revalidate=True,
                    max_age=0,
                )
                return response

            def _view(request, *args, **kwargs):
                response = view_func(request, *args, **kwargs)
                patch_cache_control(response, private=True)
                return response

            cached = cache_page(
                timeout,
                key_prefix=f"tenant-{restaurant.pk}",
            )(vary_on_headers("X-Restaurant-Slug")(_view))
            return cached(request, *args, **kwargs)

        return _wrapped

    return decorator
