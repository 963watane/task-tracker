from rest_framework.permissions import SAFE_METHODS, BasePermission

from ..models import is_manager


class IsManagerOrReadOnly(BasePermission):
    """Смотреть проекты могут все участники, создавать/менять - только менеджер."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return is_manager(request.user)


class CanEditTask(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if request.method == "DELETE":
            return obj.can_delete(request.user)
        return obj.can_edit(request.user)
