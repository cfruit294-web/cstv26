from rest_framework import serializers

from community.models import Comment, Post


class CommentSerializer(serializers.ModelSerializer):
    author_email = serializers.EmailField(source='author.email', read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'author_email', 'content', 'created_at')
        read_only_fields = ('id', 'author_email', 'created_at')


class PostSerializer(serializers.ModelSerializer):
    author_id = serializers.UUIDField(source='author.id', read_only=True)
    author_email = serializers.EmailField(source='author.email', read_only=True)
    likes_count = serializers.ReadOnlyField()
    comments_count = serializers.ReadOnlyField()
    is_liked_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = (
            'id', 'author_id', 'author_email', 'content', 'image', 'likes_count',
            'comments_count', 'is_liked_by_me', 'created_at',
        )
        read_only_fields = fields

    def get_is_liked_by_me(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.likes.filter(user=request.user).exists()


class PostCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Post
        fields = ('id', 'content', 'image')
        read_only_fields = ('id',)


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ('id', 'content')
        read_only_fields = ('id',)
