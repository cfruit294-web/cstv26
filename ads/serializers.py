from rest_framework import serializers

from ads.models import Ad


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ad
        fields = (
            'id', 'title', 'creative_type', 'placement',
            'video_file', 'image', 'duration_seconds', 'click_url',
        )
        read_only_fields = fields
