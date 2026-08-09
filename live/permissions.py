from rest_framework.permissions import SAFE_METHODS, BasePermission

from live.models import LiveStream


class CanAccessLiveStream(BasePermission):
    """Le propriétaire et les admins ont plein accès ; les autres ne voient que le contenu public non annulé."""

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_authenticated and (obj.owner_id == user.id or user.is_admin):
            return True
        if request.method in SAFE_METHODS:
            return obj.visibility == LiveStream.Visibility.PUBLIC and obj.status != LiveStream.Status.CANCELED
        return False
