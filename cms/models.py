from django.conf import settings
from django.db import models
from django.utils import timezone

from core.models import BaseModel


class Page(BaseModel):
    """Contenu éditorial statique : landing page, article de blog, FAQ, mentions légales/CGU..."""

    class PageType(models.TextChoices):
        LANDING = 'landing', "Page d'accueil"
        BLOG = 'blog', 'Article de blog'
        FAQ = 'faq', 'FAQ'
        LEGAL = 'legal', 'Mentions légales / CGU'

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cms_pages',
    )
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    page_type = models.CharField(max_length=10, choices=PageType.choices, default=PageType.BLOG)
    content = models.TextField(blank=True)
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.CharField(max_length=500, blank=True)
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-published_at', '-created_at']

    def __str__(self):
        return self.title

    def publish(self):
        self.is_published = True
        self.published_at = timezone.now()
        self.save(update_fields=['is_published', 'published_at'])
