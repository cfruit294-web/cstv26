from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from messaging.models import Conversation, Message
from messaging.serializers import (
    ConversationCreateSerializer,
    ConversationSerializer,
    MessageCreateSerializer,
    MessageSerializer,
)


class ConversationListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return ConversationCreateSerializer if self.request.method == 'POST' else ConversationSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related('participants')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        participant_ids = {str(pid) for pid in serializer.validated_data['participant_ids']}
        participant_ids.add(str(request.user.id))

        participants = list(User.objects.filter(id__in=participant_ids))
        if len(participants) != len(participant_ids):
            return Response(
                {'detail': 'Un ou plusieurs utilisateurs sont introuvables.'}, status=status.HTTP_400_BAD_REQUEST,
            )

        for conversation in Conversation.objects.filter(participants__id__in=participant_ids).distinct():
            existing_ids = {str(p.id) for p in conversation.participants.all()}
            if existing_ids == participant_ids:
                return Response(
                    ConversationSerializer(conversation, context={'request': request}).data,
                    status=status.HTTP_200_OK,
                )

        conversation = Conversation.objects.create()
        conversation.participants.set(participants)
        return Response(
            ConversationSerializer(conversation, context={'request': request}).data,
            status=status.HTTP_201_CREATED,
        )


class MessageListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return MessageCreateSerializer if self.request.method == 'POST' else MessageSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def _get_conversation(self):
        conversation = get_object_or_404(Conversation, id=self.kwargs['id'])
        if not conversation.participants.filter(id=self.request.user.id).exists():
            raise PermissionDenied('Vous ne participez pas à cette conversation.')
        return conversation

    def get_queryset(self):
        conversation = self._get_conversation()
        return Message.objects.filter(conversation=conversation).select_related('sender')

    def perform_create(self, serializer):
        conversation = self._get_conversation()
        serializer.save(sender=self.request.user, conversation=conversation)
        conversation.save()


class MarkConversationReadView(APIView):
    @extend_schema(request=None, responses=OpenApiTypes.OBJECT)
    def post(self, request, id):
        conversation = get_object_or_404(Conversation, id=id)
        if not conversation.participants.filter(id=request.user.id).exists():
            raise PermissionDenied('Vous ne participez pas à cette conversation.')

        unread_messages = list(conversation.messages.exclude(read_by=request.user))
        for message in unread_messages:
            message.read_by.add(request.user)

        return Response({'detail': 'ok', 'marked_read': len(unread_messages)})
