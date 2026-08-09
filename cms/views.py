from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics
from rest_framework.permissions import AllowAny

from accounts.permissions import IsAdminOrModerator
from cms.models import Page
from cms.serializers import PageSerializer, PageWriteSerializer


class PageListView(generics.ListAPIView):
    """Pages publiées, accessibles publiquement (landing, blog, FAQ, mentions légales...)."""

    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = Page.objects.filter(is_published=True)
        page_type = self.request.query_params.get('type')
        if page_type:
            queryset = queryset.filter(page_type=page_type)
        return queryset


class PageDetailView(generics.RetrieveAPIView):
    serializer_class = PageSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = 'slug'
    queryset = Page.objects.filter(is_published=True)


class PageAdminListCreateView(generics.ListCreateAPIView):
    """CRUD éditorial : brouillons inclus, réservé aux admins/modérateurs."""

    serializer_class = PageWriteSerializer
    permission_classes = [IsAdminOrModerator]
    queryset = Page.objects.all()

    def perform_create(self, serializer):
        was_published = serializer.validated_data.get('is_published', False)
        serializer.save(
            author=self.request.user,
            published_at=timezone.now() if was_published else None,
        )


class PageAdminDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PageWriteSerializer
    permission_classes = [IsAdminOrModerator]
    queryset = Page.objects.all()
    lookup_field = 'id'

    def perform_update(self, serializer):
        instance = self.get_object()
        now_published = serializer.validated_data.get('is_published', instance.is_published)
        if now_published and not instance.is_published:
            serializer.save(published_at=timezone.now())
        else:
            serializer.save()


def robots_txt(request):
    lines = [
        'User-agent: *',
        'Allow: /',
        f'Sitemap: {request.build_absolute_uri("/sitemap.xml")}',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain')
