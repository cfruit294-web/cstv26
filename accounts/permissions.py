from rest_framework.permissions import BasePermission, SAFE_METHODS


class HasRole(BasePermission):
    """Autorise l'accès uniquement aux utilisateurs possédant un des rôles listés."""

    allowed_roles = ()

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated
            and (user.is_superuser or user.role in self.allowed_roles)
        )


class IsAdmin(HasRole):
    allowed_roles = ('admin',)


class IsAdminOrModerator(HasRole):
    allowed_roles = ('admin', 'moderator')


class IsCreator(HasRole):
    allowed_roles = ('admin', 'creator')


class IsBusiness(HasRole):
    allowed_roles = ('admin', 'business')


class IsSupportStaff(HasRole):
    allowed_roles = ('admin', 'support')


class IsContentManager(HasRole):
    """Rôles autorisés à gérer le catalogue (import/édition des fiches)."""

    allowed_roles = ('admin', 'moderator', 'creator')


class IsSeller(HasRole):
    """Rôles autorisés à vendre des produits dans la boutique."""

    allowed_roles = ('admin', 'creator', 'business')


class IsSelfOrAdmin(BasePermission):
    """Un utilisateur ne peut consulter/modifier que son propre compte, sauf l'admin."""

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS and (request.user.is_admin or obj == request.user):
            return True
        return obj == request.user or request.user.is_admin
