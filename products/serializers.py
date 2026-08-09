from rest_framework import serializers

from products.models import Category, Product


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name', 'slug')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    seller_email = serializers.EmailField(source='seller.email', read_only=True)
    category = CategorySerializer(read_only=True)
    is_in_stock = serializers.ReadOnlyField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'product_type', 'price', 'currency',
            'cover_image', 'seller_email', 'category', 'stock_quantity', 'is_in_stock',
            'is_active', 'created_at', 'updated_at',
        )
        read_only_fields = (
            'id', 'seller_email', 'category', 'is_in_stock', 'created_at', 'updated_at',
        )


class ProductWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'description', 'product_type', 'price', 'currency',
            'cover_image', 'digital_file', 'category', 'stock_quantity', 'is_active',
        )
        read_only_fields = ('id',)

    def validate(self, attrs):
        product_type = attrs.get('product_type', getattr(self.instance, 'product_type', None))
        if product_type == Product.ProductType.PHYSICAL and attrs.get('stock_quantity') is None:
            if self.instance is None or self.instance.stock_quantity is None:
                raise serializers.ValidationError(
                    {'stock_quantity': "Le stock est obligatoire pour un produit physique."},
                )
        return attrs
