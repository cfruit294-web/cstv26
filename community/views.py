from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from community.models import Comment, Like, Post
from community.serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    PostCreateSerializer,
    PostSerializer,
)


def _can_moderate(user, instance):
    return instance.author_id == user.id or user.is_admin or user.is_moderator


class PostListCreateView(generics.ListCreateAPIView):
    queryset = Post.objects.select_related('author')

    def get_serializer_class(self):
        return PostCreateSerializer if self.request.method == 'POST' else PostSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class PostDetailView(generics.RetrieveDestroyAPIView):
    serializer_class = PostSerializer
    queryset = Post.objects.select_related('author')
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def perform_destroy(self, instance):
        if not _can_moderate(self.request.user, instance):
            raise PermissionDenied('Vous ne pouvez supprimer que vos propres publications.')
        instance.delete()


class CommentListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return CommentCreateSerializer if self.request.method == 'POST' else CommentSerializer

    def get_queryset(self):
        return Comment.objects.filter(post_id=self.kwargs['id']).select_related('author')

    def perform_create(self, serializer):
        post = get_object_or_404(Post, id=self.kwargs['id'])
        comment = serializer.save(author=self.request.user, post=post)

        if post.author_id != self.request.user.id:
            from notifications.models import Notification
            from notifications.services import notify

            notify(
                post.author,
                title=f'{self.request.user.email} a commenté votre publication',
                body=comment.content[:200],
                category=Notification.Category.COMMENT,
                link=f'/community/posts/{post.id}',
            )


class CommentDeleteView(generics.DestroyAPIView):
    serializer_class = CommentSerializer
    queryset = Comment.objects.all()
    lookup_field = 'id'

    def perform_destroy(self, instance):
        if not _can_moderate(self.request.user, instance):
            raise PermissionDenied('Vous ne pouvez supprimer que vos propres commentaires.')
        instance.delete()


class LikeToggleView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, id):
        post = get_object_or_404(Post, id=id)
        like, created = Like.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
            return Response({'liked': False, 'likes_count': post.likes.count()})
        return Response({'liked': True, 'likes_count': post.likes.count()}, status=status.HTTP_201_CREATED)
