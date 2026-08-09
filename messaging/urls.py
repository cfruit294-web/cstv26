from django.urls import path

from messaging import views

app_name = 'messaging'

urlpatterns = [
    path('conversations/', views.ConversationListCreateView.as_view(), name='conversation-list'),
    path('conversations/<uuid:id>/messages/', views.MessageListCreateView.as_view(), name='conversation-messages'),
    path('conversations/<uuid:id>/read/', views.MarkConversationReadView.as_view(), name='conversation-read'),
]
