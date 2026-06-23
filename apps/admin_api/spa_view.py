import os
import mimetypes

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.views.generic import View

DIST_DIR = os.path.join(settings.BASE_DIR, 'admin-frontend', 'dist')


class AdminSPAView(View):
    """Serve the admin frontend SPA index.html."""

    def get(self, request, *args, **kwargs):
        index_path = os.path.join(DIST_DIR, 'index.html')
        if not os.path.exists(index_path):
            return HttpResponse(
                '<h1>Admin frontend not built</h1>'
                '<p>Run: <code>cd admin-frontend && npm install && npm run build</code></p>',
                status=503,
            )
        with open(index_path, encoding='utf-8') as f:
            return HttpResponse(f.read(), content_type='text/html')


class AdminSPAAssetView(View):
    """Serve built JS/CSS assets from admin-frontend/dist/."""

    def get(self, request, path, *args, **kwargs):
        safe_path = os.path.normpath(path)
        if safe_path.startswith('..'):
            raise Http404()

        file_path = os.path.join(DIST_DIR, safe_path)
        if not os.path.isfile(file_path):
            raise Http404()

        content_type, _ = mimetypes.guess_type(file_path)
        return FileResponse(open(file_path, 'rb'), content_type=content_type or 'application/octet-stream')
