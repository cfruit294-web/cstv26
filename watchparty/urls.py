from django.urls import path

from watchparty import views

app_name = 'watchparty'

urlpatterns = [
    path('suggestions/', views.WatchPartySuggestionsView.as_view(), name='party-suggestions'),
    path('parties/', views.WatchPartyListCreateView.as_view(), name='party-list'),
    path('parties/<uuid:id>/', views.WatchPartyDetailView.as_view(), name='party-detail'),
    path('parties/<uuid:id>/join/', views.WatchPartyJoinView.as_view(), name='party-join'),
    path('parties/<uuid:id>/start/', views.WatchPartyStartView.as_view(), name='party-start'),
    path('parties/<uuid:id>/end/', views.WatchPartyEndView.as_view(), name='party-end'),
    path('parties/<uuid:id>/cancel/', views.WatchPartyCancelView.as_view(), name='party-cancel'),
    path('parties/<uuid:id>/chat/', views.WatchPartyChatHistoryView.as_view(), name='party-chat'),
    path('parties/<uuid:id>/members/', views.WatchPartyMembershipListView.as_view(), name='party-members'),
    path(
        'parties/<uuid:id>/members/<uuid:member_id>/accept/',
        views.WatchPartyMemberAcceptView.as_view(), name='party-member-accept',
    ),
    path(
        'parties/<uuid:id>/members/<uuid:member_id>/reject/',
        views.WatchPartyMemberRejectView.as_view(), name='party-member-reject',
    ),
    path(
        'parties/<uuid:id>/members/<uuid:member_id>/promote/',
        views.WatchPartyMemberPromoteView.as_view(), name='party-member-promote',
    ),
]
