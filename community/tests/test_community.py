from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from community.models import Comment, Like, Post
from notifications.models import Notification


class PostTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='author@example.com', password='S3curePass!23')
        self.other = User.objects.create_user(email='other@example.com', password='S3curePass!23')
        self.moderator = User.objects.create_user(
            email='mod@example.com', password='S3curePass!23', role=User.Role.MODERATOR,
        )

    def test_authenticated_user_can_create_post(self):
        self.client.force_authenticate(user=self.author)
        response = self.client.post(reverse('community:post-list'), {'content': 'Bonjour la communauté !'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(Post.objects.filter(author=self.author).exists())

    def test_anonymous_cannot_create_post(self):
        response = self.client.post(reverse('community:post-list'), {'content': 'x'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_posts_includes_counts_and_like_state(self):
        post = Post.objects.create(author=self.author, content='Salut')
        Like.objects.create(post=post, user=self.other)

        self.client.force_authenticate(user=self.other)
        response = self.client.get(reverse('community:post-list'))
        data = response.data['results'][0]
        self.assertEqual(data['likes_count'], 1)
        self.assertTrue(data['is_liked_by_me'])

    def test_author_can_delete_own_post(self):
        post = Post.objects.create(author=self.author, content='Salut')
        self.client.force_authenticate(user=self.author)
        response = self.client.delete(reverse('community:post-detail', args=[post.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_stranger_cannot_delete_post(self):
        post = Post.objects.create(author=self.author, content='Salut')
        self.client.force_authenticate(user=self.other)
        response = self.client.delete(reverse('community:post-detail', args=[post.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_moderator_can_delete_others_post(self):
        post = Post.objects.create(author=self.author, content='Salut')
        self.client.force_authenticate(user=self.moderator)
        response = self.client.delete(reverse('community:post-detail', args=[post.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class CommentTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='author@example.com', password='S3curePass!23')
        self.commenter = User.objects.create_user(email='commenter@example.com', password='S3curePass!23')
        self.post = Post.objects.create(author=self.author, content='Salut')

    def test_add_comment_to_post(self):
        self.client.force_authenticate(user=self.commenter)
        response = self.client.post(reverse('community:post-comments', args=[self.post.id]), {'content': 'Top !'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Comment.objects.filter(post=self.post).count(), 1)

    def test_commenting_notifies_post_author(self):
        self.client.force_authenticate(user=self.commenter)
        self.client.post(reverse('community:post-comments', args=[self.post.id]), {'content': 'Top !'})

        notification = Notification.objects.get(recipient=self.author)
        self.assertEqual(notification.category, Notification.Category.COMMENT)
        self.assertIn('Top !', notification.body)

    def test_commenting_on_own_post_does_not_notify_self(self):
        self.client.force_authenticate(user=self.author)
        self.client.post(reverse('community:post-comments', args=[self.post.id]), {'content': 'Auto-commentaire'})
        self.assertFalse(Notification.objects.filter(recipient=self.author).exists())

    def test_list_comments(self):
        Comment.objects.create(post=self.post, author=self.commenter, content='Top !')
        self.client.force_authenticate(user=self.author)
        response = self.client.get(reverse('community:post-comments', args=[self.post.id]))
        self.assertEqual(response.data['count'], 1)

    def test_author_can_delete_own_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.commenter, content='Top !')
        self.client.force_authenticate(user=self.commenter)
        response = self.client.delete(reverse('community:comment-delete', args=[comment.id]))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_stranger_cannot_delete_comment(self):
        comment = Comment.objects.create(post=self.post, author=self.commenter, content='Top !')
        stranger = User.objects.create_user(email='stranger@example.com', password='S3curePass!23')
        self.client.force_authenticate(user=stranger)
        response = self.client.delete(reverse('community:comment-delete', args=[comment.id]))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class LikeToggleTests(APITestCase):
    def setUp(self):
        self.author = User.objects.create_user(email='author@example.com', password='S3curePass!23')
        self.liker = User.objects.create_user(email='liker@example.com', password='S3curePass!23')
        self.post = Post.objects.create(author=self.author, content='Salut')
        self.client.force_authenticate(user=self.liker)

    def test_like_then_unlike_toggles(self):
        like_response = self.client.post(reverse('community:post-like', args=[self.post.id]))
        self.assertEqual(like_response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(like_response.data['liked'])
        self.assertEqual(Like.objects.filter(post=self.post, user=self.liker).count(), 1)

        unlike_response = self.client.post(reverse('community:post-like', args=[self.post.id]))
        self.assertEqual(unlike_response.status_code, status.HTTP_200_OK)
        self.assertFalse(unlike_response.data['liked'])
        self.assertEqual(Like.objects.filter(post=self.post, user=self.liker).count(), 0)
