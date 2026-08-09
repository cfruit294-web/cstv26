from django.contrib.sitemaps import Sitemap

from cms.models import Page


class PageSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.5

    def items(self):
        return Page.objects.filter(is_published=True)

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/pages/{obj.slug}/'
