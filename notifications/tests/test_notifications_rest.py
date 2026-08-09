from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from notifications.models import Notification
from notifications.services import notify


class NotificationListTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)

    def test_list_only_shows_own_notifications(self):
        notify(self.user, 'Pour moi')
        notify(self.other, 'Pas pour moi')

        response = self.client.get(reverse('notifications:notification-list'))
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Pour moi')

    def test_unread_filter(self):
        n1 = notify(self.user, 'Lu')
        notify(self.user, 'Non lu')
        n1.is_read = True
        n1.save(update_fields=['is_read'])

        response = self.client.get(reverse('notifications:notification-list'), {'unread': 'true'})
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(response.data['results'][0]['title'], 'Non lu')

    def test_unread_count(self):
        notify(self.user, 'A')
        notify(self.user, 'B')
        response = self.client.get(reverse('notifications:unread-count'))
        self.assertEqual(response.data['unread_count'], 2)


class NotificationMarkReadTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.user)

    def test_mark_single_notification_read(self):
        notification = notify(self.user, 'Titre')
        response = self.client.post(reverse('notifications:notification-read', args=[notification.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['is_read'])

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_cannot_mark_others_notification_read(self):
        notification = notify(self.other, 'Titre')
        response = self.client.post(reverse('notifications:notification-read', args=[notification.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_mark_all_read(self):
        notify(self.user, 'A')
        notify(self.user, 'B')
        notify(self.other, 'C')

        response = self.client.post(reverse('notifications:notification-read-all'))
        self.assertEqual(response.data['marked_read'], 2)
        self.assertEqual(Notification.objects.filter(recipient=self.user, is_read=False).count(), 0)
        self.assertEqual(Notification.objects.filter(recipient=self.other, is_read=False).count(), 1)
