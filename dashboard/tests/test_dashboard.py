from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from community.models import Post
from videos.models import Video


class DashboardOverviewTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(email='admin@example.com', password='S3curePass!23', role=User.Role.ADMIN)
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')

    def test_plain_user_cannot_access_dashboard(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_gets_overview_with_expected_sections(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for section in ('users', 'videos', 'live', 'community', 'messaging'):
            self.assertIn(section, response.data)

    def test_user_counts_reflect_database_state(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.data['users']['total'], 2)

    def test_community_and_video_counts(self):
        Post.objects.create(author=self.user, content='Salut')
        Video.objects.create(owner=self.user, title='Clip', status=Video.Status.READY)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response.data['community']['posts'], 1)
        self.assertEqual(response.data['videos']['ready'], 1)
