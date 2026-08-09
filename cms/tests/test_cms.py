from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from cms.models import Page


class PagePublicAccessTests(APITestCase):
    def setUp(self):
        self.published = Page.objects.create(
            title='CGU', slug='cgu', page_type=Page.PageType.LEGAL, content='Conditions...', is_published=True,
        )
        self.draft = Page.objects.create(
            title='Brouillon', slug='brouillon', page_type=Page.PageType.BLOG, content='...', is_published=False,
        )

    def test_public_list_only_shows_published_pages(self):
        response = self.client.get(reverse('cms:page-list'))
        titles = {p['title'] for p in response.data['results']}
        self.assertEqual(titles, {'CGU'})

    def test_public_can_retrieve_published_page_by_slug(self):
        response = self.client.get(reverse('cms:page-detail', args=['cgu']))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], 'CGU')

    def test_draft_page_is_not_publicly_retrievable(self):
        response = self.client.get(reverse('cms:page-detail', args=['brouillon']))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_filter_by_page_type(self):
        Page.objects.create(title='FAQ item', slug='faq-item', page_type=Page.PageType.FAQ, is_published=True)
        response = self.client.get(reverse('cms:page-list'), {'type': 'legal'})
        self.assertEqual(response.data['count'], 1)


class PageAdminManagementTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')

    def test_plain_user_cannot_create_page(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(reverse('cms:page-admin-list'), {'title': 'x', 'slug': 'x'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_create_draft_page(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('cms:page-admin-list'), {
            'title': 'Nouvel article', 'slug': 'nouvel-article', 'page_type': 'blog', 'content': 'Contenu',
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        page = Page.objects.get(slug='nouvel-article')
        self.assertFalse(page.is_published)
        self.assertIsNone(page.published_at)
        self.assertEqual(page.author, self.admin)

    def test_creating_with_is_published_sets_published_at(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.post(reverse('cms:page-admin-list'), {
            'title': 'Live', 'slug': 'live', 'is_published': True,
        })
        page = Page.objects.get(slug='live')
        self.assertTrue(page.is_published)
        self.assertIsNotNone(page.published_at)

    def test_publishing_a_draft_sets_published_at(self):
        page = Page.objects.create(title='Draft', slug='draft', is_published=False)
        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(reverse('cms:page-admin-detail', args=[page.id]), {'is_published': True})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        page.refresh_from_db()
        self.assertTrue(page.is_published)
        self.assertIsNotNone(page.published_at)

    def test_admin_list_includes_drafts(self):
        Page.objects.create(title='Draft', slug='draft-2', is_published=False)
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('cms:page-admin-list'))
        self.assertEqual(response.data['count'], 1)


class SitemapAndRobotsTests(APITestCase):
    def test_sitemap_lists_published_pages_only(self):
        Page.objects.create(title='Public', slug='public-page', is_published=True)
        Page.objects.create(title='Draft', slug='draft-page', is_published=False)

        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        content = response.content.decode()
        self.assertIn('/pages/public-page/', content)
        self.assertNotIn('/pages/draft-page/', content)

    def test_robots_txt_references_sitemap(self):
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('Sitemap:', response.content.decode())
        self.assertEqual(response['Content-Type'], 'text/plain')
