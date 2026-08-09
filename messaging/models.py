from django.conf import settings
from django.db import models

from core.models import BaseModel


class Conversation(BaseModel):
    participants = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='conversations')

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f'Conversation {self.id}'


class Message(BaseModel):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    content = models.TextField(blank=True)
    attachment = models.FileField(upload_to='messaging/attachments/', blank=True, null=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name='read_messages', blank=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'{self.sender.email}: {self.content[:30]}'
