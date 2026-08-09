from pathlib import Path

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path, reverse_lazy
from django.views.generic.base import RedirectView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication

from accounts.permissions import IsAdmin
from cms.sitemaps import PageSitemap
from cms.views import robots_txt
from videos.views import ProtectedHlsFileView, ProtectedSubtitleFileView

# Doc/schéma API réservés aux administrateurs : SessionAuthentication permet à un admin
# connecté sur /admin/ de consulter /api/docs/ directement au navigateur (JWTAuthentication
# reste dispo pour un usage programmatique via le bouton "Authorize" du Swagger UI).
_admin_only_docs = {
    'authentication_classes': [SessionAuthentication, JWTAuthentication],
    'permission_classes': [IsAdmin],
}

sitemaps = {'pages': PageSitemap}

admin.site.site_header = 'CSTV'
admin.site.site_title = 'CSTV'
admin.site.index_title = 'Administration'

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('swagger-ui'), permanent=False), name='root'),
    path('admin/', admin.site.urls),

    path('api/v1/', include('core.urls')),
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/catalog/', include('catalog.urls')),
    path('api/v1/videos/', include('videos.urls')),
    path('api/v1/live/', include('live.urls')),
    path('api/v1/community/', include('community.urls')),
    path('api/v1/messaging/', include('messaging.urls')),
    path('api/v1/dashboard/', include('dashboard.urls')),
    path('api/v1/notifications/', include('notifications.urls')),
    path('api/v1/search/', include('search.urls')),
    path('api/v1/cms/', include('cms.urls')),
    path('api/v1/watchparty/', include('watchparty.urls')),
    path('api/v1/library/', include('library.urls')),
    path('api/v1/ads/', include('ads.urls')),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='sitemap'),
    path('robots.txt', robots_txt, name='robots-txt'),

    path('api/schema/', SpectacularAPIView.as_view(**_admin_only_docs), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', **_admin_only_docs), name='swagger-ui'),

    # Fichiers media protégés : jamais servis statiquement (par nginx ou Django), toujours
    # vérifiés via un token signé temporaire. Voir core/media_access.py, videos/tokens.py.
    # Le préfixe /media/... est conservé pour rester compatible avec les URLs déjà renvoyées
    # par les FileField/serializers ; seule la route est interceptée différemment (par nginx
    # en prod via proxy_pass, ici directement par Django).
    path('media/hls/<uuid:video_id>/<path:relpath>', ProtectedHlsFileView.as_view(), name='protected-hls'),
    path(
        'media/subtitles/<uuid:video_id>/<str:language>.vtt',
        ProtectedSubtitleFileView.as_view(),
        name='protected-subtitle',
    ),
]

if settings.DEBUG:
    # Uniquement les sous-dossiers non sensibles (avatars, images communautaires, miniatures
    # vidéo, publicités) : le reste de MEDIA_ROOT (vidéos sources, HLS) ne doit JAMAIS être
    # servi directement, ni en dev ni en prod.
    for _public_prefix, _public_dir in (
        ('avatars/', 'avatars'),
        ('community/posts/', 'community/posts'),
        ('videos/thumbnails/', 'videos/thumbnails'),
        ('ads/videos/', 'ads/videos'),
        ('ads/images/', 'ads/images'),
    ):
        urlpatterns += static(
            settings.MEDIA_URL + _public_prefix,
            document_root=Path(settings.MEDIA_ROOT) / _public_dir,
        )
