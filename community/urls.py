from django.urls import path

from community import views

app_name = 'community'

urlpatterns = [
    path('posts/', views.PostListCreateView.as_view(), name='post-list'),
    path('posts/<uuid:id>/', views.PostDetailView.as_view(), name='post-detail'),
    path('posts/<uuid:id>/comments/', views.CommentListCreateView.as_view(), name='post-comments'),
    path('posts/<uuid:id>/like/', views.LikeToggleView.as_view(), name='post-like'),
    path('comments/<uuid:id>/', views.CommentDeleteView.as_view(), name='comment-delete'),
]
