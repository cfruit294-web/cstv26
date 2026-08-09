from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from messaging.models import Conversation, Message


class ConversationCreationTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', password='S3curePass!23')
        self.bob = User.objects.create_user(email='bob@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=self.alice)

    def test_create_conversation_with_another_user(self):
        response = self.client.post(reverse('messaging:conversation-list'), {'participant_ids': [str(self.bob.id)]})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        conversation = Conversation.objects.get(id=response.data['id'])
        self.assertEqual(set(conversation.participants.all()), {self.alice, self.bob})

    def test_creating_same_conversation_twice_returns_existing(self):
        first = self.client.post(reverse('messaging:conversation-list'), {'participant_ids': [str(self.bob.id)]})
        second = self.client.post(reverse('messaging:conversation-list'), {'participant_ids': [str(self.bob.id)]})
        self.assertEqual(second.status_code, status.HTTP_200_OK)
        self.assertEqual(first.data['id'], second.data['id'])
        self.assertEqual(Conversation.objects.count(), 1)

    def test_create_conversation_with_unknown_user_fails(self):
        response = self.client.post(
            reverse('messaging:conversation-list'), {'participant_ids': ['00000000-0000-0000-0000-000000000000']},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_only_shows_own_conversations(self):
        self.client.post(reverse('messaging:conversation-list'), {'participant_ids': [str(self.bob.id)]})
        stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=stranger)
        response = self.client.get(reverse('messaging:conversation-list'))
        self.assertEqual(response.data['count'], 0)


class MessageRestTests(APITestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', password='S3curePass!23')
        self.bob = User.objects.create_user(email='bob@example.com', password='S3curePass!23')
        self.stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.conversation = Conversation.objects.create()
        self.conversation.participants.set([self.alice, self.bob])

    def test_participant_can_send_message(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(
            reverse('messaging:conversation-messages', args=[self.conversation.id]), {'content': 'Salut Bob !'},
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Message.objects.filter(conversation=self.conversation).count(), 1)

    def test_message_requires_content_or_attachment(self):
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(reverse('messaging:conversation-messages', args=[self.conversation.id]), {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_non_participant_cannot_read_messages(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.get(reverse('messaging:conversation-messages', args=[self.conversation.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_participant_cannot_send_message(self):
        self.client.force_authenticate(user=self.stranger)
        response = self.client.post(
            reverse('messaging:conversation-messages', args=[self.conversation.id]), {'content': 'x'},
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_mark_conversation_read(self):
        Message.objects.create(conversation=self.conversation, sender=self.bob, content='Salut')
        self.client.force_authenticate(user=self.alice)
        response = self.client.post(reverse('messaging:conversation-read', args=[self.conversation.id]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['marked_read'], 1)

        message = Message.objects.get(conversation=self.conversation)
        self.assertTrue(message.read_by.filter(id=self.alice.id).exists())
