import json
import logging

from django.shortcuts import render, get_object_or_404
from django.contrib.auth import get_user_model
from django_filters import rest_framework as rest_framework_filters, filters
from rest_framework import (
    serializers,
    viewsets,
    decorators,
    response,
    status,
    authentication,
    exceptions,
    permissions,
)
from rest_framework.reverse import reverse
from rest_framework.authtoken import views
from rest_framework.authtoken.models import Token

from . import (
    models as account_models,
    serializers as account_serializers,
    permissions as account_permissions,
    filters as account_filters,
    authentication as account_authentication,
)
from app_core import (
    views as core_views,
)

User = get_user_model()
logger = logging.getLogger("client")


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = account_serializers.UserSerializer
    lookup_field = "pk"

    def create(self, request, *args, **kwargs):
        serializer = account_serializers.RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )


class AccountObtainAuthToken(views.ObtainAuthToken):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, created = Token.objects.get_or_create(user=user)
        if account_authentication.is_token_expired(token):
            token, created = Token.objects.get_or_create(user=user)
        return response.Response(
            {
                "token": token.key,
                # 'username': serializer.validated_data['user'].username},
                "user": account_serializers.UserSerializer(
                    user, context={"request": request}
                ).data,
            }
        )


class TeamAccessViewSet(core_views.AuthViewSetMixin, viewsets.ModelViewSet):
    permission_classes = core_views.AuthViewSetMixin.permission_classes + (
        account_permissions.TeamModelAccessPermissions,
    )
    lookup_field = "uuid"


class TeamViewSet(viewsets.ModelViewSet):
    queryset = account_models.Team.objects.all()
    serializer_class = account_serializers.TeamSerializer
    authentication_classes = (
        account_authentication.ExpiringTokenAuthentication,
        account_authentication.ApiKeyAuthentication,
    )
    filter_backends = (account_filters.TeamFilterBackend,)
    filterset_class = account_filters.TeamFilterSet
    lookup_field = "uuid"

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        team = self.perform_create(serializer)
        membership = account_models.Membership.objects.create(
            team=team, user=request.user, role=account_models.Membership.Role.ADMIN
        )
        headers = self.get_success_headers(serializer.data)
        return response.Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        return serializer.save()

    @decorators.action(
        detail=False,
        methods=["get"],
        url_name="all_teams",
        permission_classes=(permissions.IsAuthenticated,),
        filter_backends=(rest_framework_filters.DjangoFilterBackend,),
    )
    def all_teams(self, request, *args, **kwargs):
        """
        Return all teams in database with pagination
        Override list method with different filter backend and permission
        """
        return self.list(request, *args, **kwargs)

    @decorators.action(detail=True, methods=["post"], url_name="user_add")
    def user_add(self, request, uuid=None):
        # TODO: check permission of owner of the team
        team = self.get_object()
        # can be both TeamUserAddSerializer and TeamSerializer
        serializer = account_serializers.TeamUserAddSerializer(data=request.POST)
        if serializer.is_valid():
            for user in serializer.validated_data["users"]:
                membership = account_models.Membership.objects.create(
                    team=team, user=user, role=account_models.Membership.Role.GENERAL
                )
            team.save()
            return response.Response(
                self.serializer_class(team, context={"request": request}).data,
                status=status.HTTP_200_OK,
            )
        else:
            return response.Response(
                serializer.errors, status=status.HTTP_400_BAD_REQUEST
            )

    @decorators.action(detail=True, methods=["post"], url_name="user_remove")
    def user_remove(self, request, uuid=None):
        instance = self.get_object()
        serializer = account_serializers.TeamUserAddSerializer(data=request.POST)
        if serializer.is_valid():
            memberships = account_models.Membership.objects.filter(
                team=instance,
                user__in=serializer.validated_data["users"],
            )
            for m in memberships:
                m.delete()
        instance.save()
        return response.Response({}, status=status.HTTP_200_OK)


class InvitationViewSet(TeamAccessViewSet):
    queryset = account_models.Invitation.objects.all()
    serializer_class = account_serializers.InvitationSerializer
    permission_classes = (
        account_permissions.InvitationPermissions & permissions.IsAuthenticated,
    )
    filter_backends = (account_filters.InvitationFilterBackend,)
    filterset_class = account_filters.InvitationFilterSet

    def perform_create(self, serializer):
        # Check if the user is already in the team
        try:
            user = account_models.User.objects.get(
                email=serializer.validated_data["email"]
            )
            if user.id in serializer.validated_data["team"].members:
                raise exceptions.ValidationError("The user is already in the team")
        except account_models.User.DoesNotExist:
            # If the user does not exists, it is not in the team
            pass

        invitation = serializer.save(invited_by=self.request.user)
        # send_invitation(invitation)
        return

    @decorators.action(
        detail=True,
        methods=["get"],
        url_name="accept",
    )
    def accept(self, request, uuid=None):
        invitation = self.get_object()
        if invitation.is_accepted:
            raise exceptions.PermissionDenied("the invitation link is expired")

        user = get_object_or_404(User, email=invitation.email)
        if invitation.invited_by.email != invitation.email:
            # This state means the user is invited by a team. So, only itself can accept
            if user != request.user:
                raise exceptions.PermissionDenied()

        membership = account_models.Membership.objects.create(
            user=user, team=invitation.team, role=invitation.role
        )

        invitation.is_accepted = True
        invitation.accepted_by = request.user
        invitation.save()

        return response.Response(
            account_serializers.InvitationSerializer(
                invitation, context={"request": request}
            ).data,
            status=status.HTTP_202_ACCEPTED,
        )

    @decorators.action(detail=True, methods=["get"], url_name="reject")
    def reject(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)


class JoinRequestViewSet(viewsets.ModelViewSet):
    queryset = account_models.Invitation.objects.all()
    serializer_class = account_serializers.InvitationSerializer
    permission_classes = (
        account_permissions.JoinRequestPermissions & permissions.IsAuthenticated,
    )
    filter_backends = (account_filters.JoinRequestFilterBackend,)
    filterset_class = account_filters.InvitationFilterSet

    def perform_create(self, serializer):
        # there is no need to add extra data to detect if it is an invitation or join request
        # They can be detected by filtering
        if self.request.user.id in serializer.validated_data["team"].members:
            raise exceptions.ValidationError("The user is already in the team")
        if self.request.user.email != serializer.validated_data["email"]:
            raise exceptions.ValidationError("Invalid email address")
        join_request = serializer.save(invited_by=self.request.user)


class AccountAPIKeyViewSet(TeamAccessViewSet):
    queryset = account_models.AccountAPIKey.objects.all()
    serializer_class = account_serializers.AccountAPIKeySerializer
    permission_classes = ()  # TODO: complete
    filter_backends = (account_filters.ApiKeyTeamAccessFilterBackend,)
    filterset_class = account_filters.ApiKeyTeamAccessFilterSet
    http_method_names = ["get", "post", "delete", "head"]
