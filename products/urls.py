from django.urls import path

from products import views

app_name = 'products'

urlpatterns = [
    path('categories/', views.CategoryListView.as_view(), name='category-list'),
    path('categories/admin/', views.CategoryAdminCreateView.as_view(), name='category-admin-list'),
    path('', views.ProductListView.as_view(), name='product-list'),
    path('mine/', views.MyProductsView.as_view(), name='product-mine'),
    path('create/', views.ProductCreateView.as_view(), name='product-create'),
    path('<uuid:id>/', views.ProductDetailView.as_view(), name='product-detail'),
    path('<uuid:id>/manage/', views.ProductUpdateDeleteView.as_view(), name='product-manage'),
]
