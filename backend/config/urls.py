from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import include, path, re_path
from django.conf import settings
from django.conf.urls.static import static
from pathlib import Path


def _spa_file(filename):
    target = (Path(settings.FRONTEND_DIST_DIR) / filename)
    if not target.exists() or not target.is_file():
        raise Http404(f'{filename} not found')
    return FileResponse(open(target, 'rb'))


def _spa_index():
    index = Path(settings.FRONTEND_DIST_DIR) / 'index.html'
    if not index.exists():
        raise Http404('Frontend build not found. Run: cd frontend && npm run build, then copy dist/ to backend/frontend_dist/.')
    return FileResponse(open(index, 'rb'), content_type='text/html')


def spa_view(request, _path=''):
    # /assets/... -> serve the hashed Vite bundle from frontend_dist
    if _path.startswith('assets/'):
        return _spa_file(_path)
    # /vite.svg, /favicon.* etc.
    suffix = Path(_path).suffix.lower()
    if suffix in ('.svg', '.ico', '.png', '.jpg', '.jpeg', '.webp', '.txt', '.xml', '.json', '.webmanifest'):
        try:
            return _spa_file(_path)
        except Http404:
            pass
    return _spa_index()


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('jobs.urls')),
    # React SPA: app shell for every non-API route (/, /jobs, /login, ...)
    path('', spa_view, name='spa-root'),
    re_path(r'^(?P<_path>(?!api/|admin/|static/|media/).*)$', spa_view, name='spa'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
