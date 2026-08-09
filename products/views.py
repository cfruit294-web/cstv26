from django.db.models import Q
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated

from accounts.permissions import IsAdmin, IsSeller
from products.models import Category, Product
from products.permissions import IsOwnerOrReadOnly
from products.serializers import CategorySerializer, ProductSerializer, ProductWriteSerializer


class CategoryListView(generics.ListAPIView):
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    queryset = Category.objects.all()


class CategoryAdminCreateView(generics.ListCreateAPIView):
    serializer_class = CategorySerializer
    permission_classes = [IsAdmin]
    queryset = Category.objects.all()


class ProductListView(generics.ListAPIView):
    """Catalogue public : produits actifs, filtrables par catégorie/type/recherche."""

    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    def get_queryset(self):
        queryset = Product.objects.filter(is_active=True).select_related('seller', 'category')
        category_slug = self.request.query_params.get('category')
        product_type = self.request.query_params.get('type')
        search = self.request.query_params.get('q')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return queryset


class ProductDetailView(generics.RetrieveAPIView):
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    lookup_field = 'id'

    def get_queryset(self):
        return Product.objects.select_related('seller', 'category')


class MyProductsView(generics.ListAPIView):
    """Le vendeur voit tous ses produits, y compris désactivés."""

    serializer_class = ProductSerializer
    permission_classes = [IsSeller]

    def get_queryset(self):
        return Product.objects.filter(seller=self.request.user).select_related('seller', 'category')


class ProductCreateView(generics.CreateAPIView):
    serializer_class = ProductWriteSerializer
    permission_classes = [IsSeller]

    def perform_create(self, serializer):
        serializer.save(seller=self.request.user)


class ProductUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ProductWriteSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    lookup_field = 'id'
    queryset = Product.objects.all()
