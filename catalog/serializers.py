from rest_framework import serializers

from catalog.models import Movie


class MovieSerializer(serializers.ModelSerializer):
    class Meta:
        model = Movie
        fields = (
            'id', 'imdb_id', 'title', 'year', 'type', 'rated', 'runtime_minutes',
            'genre', 'director', 'actors', 'plot', 'poster_url', 'imdb_rating',
            'created_at', 'updated_at',
        )
        read_only_fields = fields


class MovieImportSerializer(serializers.Serializer):
    imdb_id = serializers.CharField(required=False, allow_blank=True)
    title = serializers.CharField(required=False, allow_blank=True)
    year = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        if not attrs.get('imdb_id') and not attrs.get('title'):
            raise serializers.ValidationError("Fournissez 'imdb_id' ou 'title'.")
        return attrs


class OmdbSearchQuerySerializer(serializers.Serializer):
    q = serializers.CharField()
    page = serializers.IntegerField(required=False, default=1, min_value=1)
