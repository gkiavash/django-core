import uuid

from django.db.models import Q
from django_filters import rest_framework as rest_framework_filters, filters
from . import models as account_models


class TeamFilterBackend(rest_framework_filters.DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        queryset = queryset.filter(memberships__user=request.user)
        return super().filter_queryset(request, queryset, view)


class TeamFilterSet(rest_framework_filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="contains")

    class Meta:
        model = account_models.Team
        fields = ("name",)


class InvitationFilterBackend(rest_framework_filters.DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_superuser:
            queryset = queryset.filter(
                Q(team__memberships__user=request.user) | Q(email=request.user.email)
            ).distinct()
        queryset = super().filter_queryset(request, queryset, view)
        return queryset


class InvitationFilterSet(rest_framework_filters.FilterSet):
    team_uuid = filters.CharFilter(field_name="team__uuid")
    is_accepted = filters.BooleanFilter(field_name="is_accepted")
    invited_by = filters.CharFilter(field_name="invited_by__id")


class JoinRequestFilterBackend(rest_framework_filters.DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        if not request.user.is_superuser:
            queryset = queryset.filter(
                Q(invited_by=request.user) & Q(email=request.user.email),
            ).distinct()
        queryset = super().filter_queryset(request, queryset, view)
        return queryset


class ApiKeyTeamAccessFilterBackend(rest_framework_filters.DjangoFilterBackend):
    def filter_queryset(self, request, queryset, view):
        queryset = queryset.filter(team__memberships__user=request.user)
        return super().filter_queryset(request, queryset, view)


class ApiKeyTeamAccessFilterSet(rest_framework_filters.FilterSet):
    owner_uuid = filters.CharFilter(field_name="team__uuid")
