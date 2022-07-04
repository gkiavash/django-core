from django.db.models import Q
from rest_framework import permissions
from rest_framework import exceptions, request
from rest_framework_api_key.permissions import HasAPIKey

from . import models as account_models


class TeamModelAccessPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return account_models.Membership.objects.filter(
            user=request.user, team=obj.owner
        ).exists()


class RequestHasAPIKey(HasAPIKey):
    model = account_models.AccountAPIKey

    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj)


class InvitationPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        return account_models.Invitation.objects.filter(
            Q(team__memberships__user=request.user) | Q(email=request.user.email)
        ).exists()


class JoinRequestPermissions(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user.is_superuser:
            if obj.invited_by == request.user and obj.email == request.user.email:
                return True
        return False
