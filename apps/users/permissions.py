from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsSubscriber(BasePermission):
    message = "You need an active subscription to perform this action."

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.has_active_subscription
        )


class IsOwnerOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        return obj.author == request.user or request.user.is_staff

