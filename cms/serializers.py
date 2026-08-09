from rest_framework import serializers

from cms.models import Page


class PageSerializer(serializers.ModelSerializer):
    author_email = serializers.SerializerMethodField()

    class Meta:
        model = Page
        fields = (
            'id', 'title', 'slug', 'page_type', 'content', 'meta_title',
            'meta_description', 'author_email', 'published_at', 'created_at',
        )
        read_only_fields = fields

    def get_author_email(self, obj) -> str:
        return obj.author.email if obj.author else ''


class PageWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Page
        fields = (
            'id', 'title', 'slug', 'page_type', 'content',
            'meta_title', 'meta_description', 'is_published', 'published_at',
        )
        read_only_fields = ('id', 'published_at')
