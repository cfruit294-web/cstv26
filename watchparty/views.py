from django.db.models import Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.models import Movie
from catalog.serializers import MovieSerializer
from videos.models import Video
from watchparty.models import WatchParty, WatchPartyChatMessage, WatchPartyMembership
from watchparty.serializers import (
    WatchPartyChatMessageSerializer,
    WatchPartyCreateSerializer,
    WatchPartyMembershipSerializer,
    WatchPartySerializer,
)

SUGGESTION_COUNT = 12


def _user_genre_keywords(user):
    """Genres des films des séances déjà organisées ou suivies par l'utilisateur (signal de goût)."""
    hosted = WatchParty.objects.filter(host=user)
    attended = WatchParty.objects.filter(
        memberships__user=user, memberships__status=WatchPartyMembership.Status.ACCEPTED,
    )
    genre_values = (hosted | attended).exclude(video__movie__isnull=True).values_list('video__movie__genre', flat=True)

    keywords = set()
    for genre_field in genre_values:
        if genre_field:
            keywords.update(part.strip() for part in genre_field.split(',') if part.strip())
    return keywords


def _is_accepted_member(user, party):
    return party.host_id == user.id or WatchPartyMembership.objects.filter(
        party=party, user=user, status=WatchPartyMembership.Status.ACCEPTED,
    ).exists()


def _can_moderate(user, party):
    if party.host_id == user.id:
        return True
    return WatchPartyMembership.objects.filter(
        party=party, user=user, status=WatchPartyMembership.Status.ACCEPTED,
        role=WatchPartyMembership.Role.MODERATOR,
    ).exists()


class WatchPartySuggestionsView(generics.ListAPIView):
    """Films avec vidéo publique disponible, triés selon les genres déjà regardés par l'utilisateur.

    Utilisé pour proposer des films au moment de créer une séance : sans historique, on retombe sur
    les mieux notés du catalogue.
    """

    serializer_class = MovieSerializer
    pagination_class = None

    def get_queryset(self):
        eligible = Movie.objects.filter(
            videos__status=Video.Status.READY, videos__visibility=Video.Visibility.PUBLIC,
        ).distinct()

        keywords = _user_genre_keywords(self.request.user)
        if keywords:
            genre_query = Q()
            for keyword in keywords:
                genre_query |= Q(genre__icontains=keyword)
            personalized = eligible.filter(genre_query).order_by('-imdb_rating')
            if personalized.exists():
                return personalized[:SUGGESTION_COUNT]

        return eligible.order_by('-imdb_rating')[:SUGGESTION_COUNT]


class WatchPartyListCreateView(generics.ListCreateAPIView):
    """Liste les séances non annulées ; la création choisit une vidéo publique déjà prête et une heure."""

    queryset = WatchParty.objects.exclude(status=WatchParty.Status.CANCELED).select_related('host', 'video')

    def get_serializer_class(self):
        return WatchPartyCreateSerializer if self.request.method == 'POST' else WatchPartySerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        party = serializer.save(host=request.user)
        return Response(WatchPartySerializer(party, context={'request': request}).data, status=status.HTTP_201_CREATED)


class WatchPartyDetailView(generics.RetrieveAPIView):
    serializer_class = WatchPartySerializer
    queryset = WatchParty.objects.select_related('host', 'video')
    lookup_field = 'id'

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


class WatchPartyJoinView(APIView):
    """Envoie une demande pour rejoindre la séance (ré-utilisable après un refus)."""

    @extend_schema(request=None, responses=WatchPartyMembershipSerializer)
    def post(self, request, id):
        party = get_object_or_404(WatchParty, id=id)
        if party.host_id == request.user.id:
            return Response({'detail': "Tu es déjà l'hôte de cette séance."}, status=status.HTTP_400_BAD_REQUEST)

        membership, created = WatchPartyMembership.objects.get_or_create(party=party, user=request.user)
        if not created:
            if membership.status in (WatchPartyMembership.Status.PENDING, WatchPartyMembership.Status.ACCEPTED):
                return Response(
                    {'detail': 'Tu as déjà une demande envoyée ou en cours pour cette séance.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            membership.status = WatchPartyMembership.Status.PENDING
            membership.save(update_fields=['status'])

        return Response(WatchPartyMembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class WatchPartyMembershipListView(generics.ListAPIView):
    """Réservé à l'hôte/modérateur : liste des demandes et membres pour gérer les accès."""

    serializer_class = WatchPartyMembershipSerializer

    def get_queryset(self):
        party = get_object_or_404(WatchParty, id=self.kwargs['id'])
        if not _can_moderate(self.request.user, party):
            raise PermissionDenied("Seuls l'hôte et les modérateurs peuvent voir les demandes.")
        return WatchPartyMembership.objects.filter(party=party).select_related('user')


class WatchPartyMemberAcceptView(APIView):
    @extend_schema(request=None, responses=WatchPartyMembershipSerializer)
    def post(self, request, id, member_id):
        party = get_object_or_404(WatchParty, id=id)
        if not _can_moderate(request.user, party):
            raise PermissionDenied("Seuls l'hôte et les modérateurs peuvent accepter des demandes.")
        membership = get_object_or_404(WatchPartyMembership, id=member_id, party=party)
        membership.status = WatchPartyMembership.Status.ACCEPTED
        membership.save(update_fields=['status'])
        return Response(WatchPartyMembershipSerializer(membership).data)


class WatchPartyMemberRejectView(APIView):
    @extend_schema(request=None, responses=WatchPartyMembershipSerializer)
    def post(self, request, id, member_id):
        party = get_object_or_404(WatchParty, id=id)
        if not _can_moderate(request.user, party):
            raise PermissionDenied("Seuls l'hôte et les modérateurs peuvent refuser des demandes.")
        membership = get_object_or_404(WatchPartyMembership, id=member_id, party=party)
        membership.status = WatchPartyMembership.Status.REJECTED
        membership.save(update_fields=['status'])
        return Response(WatchPartyMembershipSerializer(membership).data)


class WatchPartyMemberPromoteView(APIView):
    """Réservé à l'hôte : nomme un membre déjà accepté modérateur (peut accepter/refuser, contrôler la lecture)."""

    @extend_schema(request=None, responses=WatchPartyMembershipSerializer)
    def post(self, request, id, member_id):
        party = get_object_or_404(WatchParty, id=id)
        if party.host_id != request.user.id:
            raise PermissionDenied("Seul l'hôte peut nommer un modérateur.")
        membership = get_object_or_404(
            WatchPartyMembership, id=member_id, party=party, status=WatchPartyMembership.Status.ACCEPTED,
        )
        membership.role = WatchPartyMembership.Role.MODERATOR
        membership.save(update_fields=['role'])
        return Response(WatchPartyMembershipSerializer(membership).data)


class WatchPartyStartView(APIView):
    @extend_schema(request=None, responses=WatchPartySerializer)
    def post(self, request, id):
        party = get_object_or_404(WatchParty, id=id)
        if not _can_moderate(request.user, party):
            raise PermissionDenied("Seuls l'hôte et les modérateurs peuvent démarrer la séance.")
        party.status = WatchParty.Status.LIVE
        party.save(update_fields=['status'])
        return Response(WatchPartySerializer(party, context={'request': request}).data)


class WatchPartyEndView(APIView):
    @extend_schema(request=None, responses=WatchPartySerializer)
    def post(self, request, id):
        party = get_object_or_404(WatchParty, id=id)
        if not _can_moderate(request.user, party):
            raise PermissionDenied("Seuls l'hôte et les modérateurs peuvent terminer la séance.")
        party.status = WatchParty.Status.ENDED
        party.is_playing = False
        party.save(update_fields=['status', 'is_playing'])
        return Response(WatchPartySerializer(party, context={'request': request}).data)


class WatchPartyCancelView(APIView):
    @extend_schema(request=None, responses=WatchPartySerializer)
    def post(self, request, id):
        party = get_object_or_404(WatchParty, id=id)
        if party.host_id != request.user.id:
            raise PermissionDenied("Seul l'hôte peut annuler la séance.")
        if party.status != WatchParty.Status.SCHEDULED:
            return Response(
                {'detail': 'Seule une séance encore planifiée peut être annulée.'}, status=status.HTTP_400_BAD_REQUEST,
            )
        party.status = WatchParty.Status.CANCELED
        party.save(update_fields=['status'])
        return Response(WatchPartySerializer(party, context={'request': request}).data)


class WatchPartyChatHistoryView(generics.ListAPIView):
    serializer_class = WatchPartyChatMessageSerializer

    def get_queryset(self):
        party = get_object_or_404(WatchParty, id=self.kwargs['id'])
        if not _is_accepted_member(self.request.user, party):
            raise PermissionDenied("Tu n'as pas accès à cette séance.")
        return WatchPartyChatMessage.objects.filter(party=party).select_related('user')
