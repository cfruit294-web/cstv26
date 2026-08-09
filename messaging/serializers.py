from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from messaging.models import Conversation, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_email = serializers.EmailField(source='sender.email', read_only=True)
    is_read_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = ('id', 'sender_email', 'content', 'attachment', 'is_read_by_me', 'created_at')
        read_only_fields = fields

    def get_is_read_by_me(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            return False
        return obj.read_by.filter(id=request.user.id).exists()


class MessageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Message
        fields = ('id', 'content', 'attachment')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if not attrs.get('content') and not attrs.get('attachment'):
            raise serializers.ValidationError("Le message doit contenir du texte ou une pièce jointe.")
        return attrs


class ConversationSerializer(serializers.ModelSerializer):
    participant_emails = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ('id', 'participant_emails', 'last_message', 'created_at', 'updated_at')
        read_only_fields = fields

    def get_participant_emails(self, obj) -> list[str]:
        return [user.email for user in obj.participants.all()]

    @extend_schema_field(MessageSerializer)
    def get_last_message(self, obj):
        last = obj.messages.order_by('-created_at').first()
        return MessageSerializer(last, context=self.context).data if last else None


class ConversationCreateSerializer(serializers.Serializer):
    participant_ids = serializers.ListField(child=serializers.UUIDField(), min_length=1)
