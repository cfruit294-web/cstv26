from django.urls import path

from cms import views

app_name = 'cms'

urlpatterns = [
    path('pages/', views.PageListView.as_view(), name='page-list'),
    path('pages/admin/', views.PageAdminListCreateView.as_view(), name='page-admin-list'),
    path('pages/admin/<uuid:id>/', views.PageAdminDetailView.as_view(), name='page-admin-detail'),
    path('pages/<slug:slug>/', views.PageDetailView.as_view(), name='page-detail'),
]
