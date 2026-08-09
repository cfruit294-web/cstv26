from rest_framework.permissions import SAFE_METHODS, BasePermission

from videos.models import Video


class CanAccessVideo(BasePermission):
    """Le propriétaire et les admins ont plein accès ; les autres ne voient que le contenu public prêt."""

    def has_object_permission(self, request, view, obj):
        if obj.owner_id == request.user.id or request.user.is_admin:
            return True
        if request.method in SAFE_METHODS:
            return obj.status == Video.Status.READY and obj.visibility == Video.Visibility.PUBLIC
        return False
