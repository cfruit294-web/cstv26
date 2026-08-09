from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsOwnerOrReadOnly(BasePermission):
    """Le vendeur (ou un admin) peut modifier/supprimer ; tout le monde peut lire."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.seller_id == request.user.id or request.user.is_admin
