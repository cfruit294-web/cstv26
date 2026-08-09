from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsContentManager
from catalog import services
from catalog.models import Movie
from catalog.serializers import MovieImportSerializer, MovieSerializer, OmdbSearchQuerySerializer


class OmdbSearchView(APIView):
    """Recherche en direct sur OMDb par titre (aucune écriture en base)."""

    @extend_schema(
        parameters=[
            OpenApiParameter('q', OpenApiTypes.STR, required=True, description='Titre recherché'),
            OpenApiParameter('page', OpenApiTypes.INT, required=False),
        ],
        responses=OpenApiTypes.OBJECT,
    )
    def get(self, request):
        serializer = OmdbSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        try:
            result = services.search(**serializer.validated_data)
        except services.OmdbError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        return Response(result)


class MovieImportView(APIView):
    """Importe (ou met à jour) une fiche film/série depuis OMDb dans le catalogue local."""

    permission_classes = [IsContentManager]

    @extend_schema(request=MovieImportSerializer, responses=MovieSerializer)
    def post(self, request):
        serializer = MovieImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        try:
            if payload.get('imdb_id'):
                data = services.fetch_by_imdb_id(payload['imdb_id'])
            else:
                data = services.fetch_by_title(payload['title'], payload.get('year'))
        except services.OmdbError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        fields = services.to_movie_fields(data)
        imdb_id = fields.pop('imdb_id')
        movie, _created = Movie.objects.update_or_create(
            imdb_id=imdb_id,
            defaults={**fields, 'imported_by': request.user},
        )
        return Response(MovieSerializer(movie).data, status=status.HTTP_201_CREATED)


class MovieListView(generics.ListAPIView):
    """Parcourt le catalogue local déjà importé (pas d'appel OMDb)."""

    serializer_class = MovieSerializer
    queryset = Movie.objects.all()
    permission_classes = [AllowAny]

    ORDERING_FIELDS = {
        'imdb_rating': 'imdb_rating',
        '-imdb_rating': '-imdb_rating',
        'created_at': 'created_at',
        '-created_at': '-created_at',
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(title__icontains=query)

        movie_type = self.request.query_params.get('type')
        if movie_type in dict(Movie.Type.choices):
            queryset = queryset.filter(type=movie_type)

        genre = self.request.query_params.get('genre')
        if genre:
            queryset = queryset.filter(genre__icontains=genre)

        ordering = self.ORDERING_FIELDS.get(self.request.query_params.get('ordering'))
        if ordering:
            queryset = queryset.order_by(ordering)

        return queryset


class MovieDetailView(generics.RetrieveAPIView):
    serializer_class = MovieSerializer
    queryset = Movie.objects.all()
    lookup_field = 'id'
    permission_classes = [AllowAny]


class MovieRecommendationsView(generics.ListAPIView):
    """Films à recommander sous la fiche d'un film (même genre/acteurs en priorité)."""

    serializer_class = MovieSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        movie = get_object_or_404(Movie, id=self.kwargs['id'])
        return services.get_recommended_movies(movie)
