from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from model_utils.models import TimeStampedModel
from rest_framework import exceptions
from rest_framework_api_key.models import AbstractAPIKey

from app_core import mixins as core_mixins


class User(AbstractUser):
    @property
    def teams(self):
        return Team.objects.filter(
            id__in=self.memberships.all().values_list("team", flat=True)
        )


class Team(core_mixins.UuidMixin, TimeStampedModel, models.Model):
    name = models.CharField(
        _("name"), max_length=150, null=True, blank=True, unique=True
    )

    @property
    def members(self):
        return self.memberships.all().values_list("user", flat=True)


class Membership(TimeStampedModel, models.Model):
    """
    A user's team membership
    """

    class Role:
        ADMIN = "ADMIN"
        GENERAL = "GENERAL"
        CONFIGURATION = "CONFIGURATION"

        CHOICES = (
            (ADMIN, "ADMIN"),
            (GENERAL, "GENERAL"),
            (CONFIGURATION, "CONFIGURATION"),
        )

    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="memberships"
    )
    role = models.CharField(max_length=100, default=Role.GENERAL, choices=Role.CHOICES)

    class Meta:
        unique_together = ("user", "team")


class Invitation(core_mixins.UuidMixin, TimeStampedModel, models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="invitations")
    email = models.EmailField()
    role = models.CharField(
        max_length=100, choices=Membership.Role.CHOICES, default=Membership.Role.GENERAL
    )
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_invitations",
        null=True,
        blank=True,
    )
    is_accepted = models.BooleanField(default=False)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accepted_invitations",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("team", "email")


class AccountAPIKey(core_mixins.UuidMixin, AbstractAPIKey):
    key = models.CharField(max_length=300, default="", null=True, blank=True)

    team = models.ForeignKey(
        Team, on_delete=models.CASCADE, related_name="api_keys", null=True, blank=True
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="api_keys",
        null=True,
        blank=True,
    )

    class Meta:
        unique_together = ("name", "team")
