from rest_framework import serializers

from catalog.serializers import MovieSerializer
from library.models import WatchHistory, WatchlistItem


class WatchlistItemSerializer(serializers.ModelSerializer):
    movie = MovieSerializer(read_only=True)

    class Meta:
        model = WatchlistItem
        fields = ('id', 'movie', 'created_at')
        read_only_fields = fields


class WatchHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = WatchHistory
        fields = ('id', 'video', 'position_seconds', 'updated_at')
        read_only_fields = ('id', 'updated_at')
