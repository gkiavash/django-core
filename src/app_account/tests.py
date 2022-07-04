import json
import logging
import unittest
from unittest import skip

from django.contrib.auth import get_user_model
from django.utils import timezone
from django.conf import settings
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework import status, exceptions
from rest_framework.authtoken.models import Token


from . import (
    models as account_models,
    authentication as account_authentication
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CoreTests(APITestCase):
    def setUp(self):
        self.user_1 = User.objects.create_user(
            "user_1", password="test", email="test1@test.test"
        )
        self.user_2 = User.objects.create_user(
            "user_2", password="test", email="test2@test.test"
        )
        self.team_1 = account_models.Team.objects.create(name="AwesomeCustomer")
        self.membership = account_models.Membership.objects.create(
            user=self.user_1,
            team=self.team_1,
            role=account_models.Membership.Role.ADMIN,
        )
        self.user_config_team_1 = self.make_user_configuration(self.team_1)

    def make_user_configuration(self, team, prefix=""):
        user_config = User.objects.create_user(
            f"user_config_{prefix}_{team.name}",
            password="test",
            email=f"user_config_{team.name}@test.test",
        )
        self.membership = account_models.Membership.objects.create(
            user=user_config,
            team=team,
            role=account_models.Membership.Role.CONFIGURATION,
        )
        self.api_key_obj, key = account_models.AccountAPIKey.objects.create_key(
            name=f"test_{team.name}_{prefix}"
        )
        self.api_key_obj.user = user_config
        self.api_key_obj.team = team
        self.api_key_obj.key = key
        self.api_key_obj.save()
        return user_config

    def get_token(self, user):
        response = self.client.post(
            reverse(
                "login",
            ),
            data={
                "username": user.username,
                "password": "test",
            },
            follow=True,
        )
        return response.json().get("token")

    def get_token_header(self, user):
        return f"Token {self.get_token(user)}"

    def get_api_key_header(self, api_key_user=None, team=None):
        if api_key_user and team:
            api_key_obj = account_models.AccountAPIKey.objects.filter(
                user=api_key_user, team=team
            ).last()
            return f"Api-Key {api_key_obj.key}"
        return f"Api-Key {self.api_key_obj.key}"


class TeamTests(CoreTests):
    def setUp(self):
        super().setUp()
        # To test search teams with different names
        self.team_3 = account_models.Team.objects.create(name="WrongCustomer3")
        self.membership = account_models.Membership.objects.create(
            user=self.user_2,
            team=self.team_3,
            role=account_models.Membership.Role.ADMIN,
        )

    def test_team_name_uniqueness(self):
        team_2 = account_models.Team.objects.create(name="t2")

        # TEST UNIQUENESS TEAM NAME
        response = self.client.post(
            reverse("team-list"),
            data={"name": "t2"},
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # TEST UNIQUENESS TEAM NAME FROM DIFFERENT USER
        response = self.client.post(
            reverse("team-list"),
            data={"name": "t2"},
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_2),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_team_list(self):
        response = self.client.get(
            reverse("team-list"),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        print(response.json())
        self.assertEqual(response.json()["count"], 1)

    def test_team_get_by_api_key(self):
        response = self.client.get(
            reverse("team-list"),
            follow=True,
            HTTP_AUTHORIZATION=self.get_api_key_header(
                self.user_config_team_1, self.team_1
            ),
        )
        self.assertEqual(response.json()["count"], 1)
        # it should be one team. because config user is can only be in one team


class InvitationTests(CoreTests):
    def setUp(self):
        super().setUp()
        self.user_3 = User.objects.create_user(
            username="test3", password="test", email="t3@test.com"
        )
        self.invitation = account_models.Invitation.objects.create(
            team=self.team_1, email=self.user_3.email, invited_by=self.user_1
        )
        self.user_4 = User.objects.create_user(
            username="test4", password="test", email="t4@test.com"
        )

    def test_invitation_accept_fails(self):
        """
        Accept by other users is forbidden
        This invitation is for user_3
        """
        response = self.client.get(
            reverse("invitation-accept", kwargs={"uuid": self.invitation.uuid}),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_invitation_accept(self):
        response = self.client.get(
            reverse("invitation-accept", kwargs={"uuid": self.invitation.uuid}),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_3),
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.invitation.team.refresh_from_db()
        self.assertIn(self.user_3.pk, [u for u in self.invitation.team.members.all()])

    def test_invitation_reject(self):
        response = self.client.get(
            reverse("invitation-reject", kwargs={"uuid": self.invitation.uuid}),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_3),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(
            account_models.Invitation.objects.filter(id=self.invitation.id).exists(),
            False,
        )

    def test_invitation_unique_email(self):
        self.client.force_authenticate(user=self.user_1)
        response = self.client.post(
            reverse(
                "invitation-list",
            ),
            data={
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
                "email": "t@teat.com",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        response = self.client.post(
            reverse(
                "invitation-list",
            ),
            data={
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
                "email": "t@teat.com",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invitation_list_filter(self):
        """
        user from the team should see all invitations to its own team
        user from no team should see only his invitations to other teams
        """
        response = self.client.post(
            reverse(
                "invitation-list",
            ),
            data={
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
                "email": self.user_4.email,
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        response = self.client.post(
            reverse(
                "invitation-list",
            ),
            data={
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
                "email": "t5@test.com",
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        response = self.client.get(
            reverse(
                "invitation-list",
            ),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_4),
        )
        self.assertEqual(response.json()["count"], 1)

        response = self.client.get(
            reverse(
                "invitation-list",
            ),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.json()["count"], 3)


class JoinRequestTests(CoreTests):
    def setUp(self):
        super().setUp()
        self.user_3 = User.objects.create_user(
            username="test3", password="test", email="t3@test.com"
        )
        # JOIN REQUEST user_3 => team_1
        join_request = account_models.Invitation.objects.create(
            team=self.team_1, email=self.user_3.email, invited_by=self.user_3
        )

        self.team_2 = account_models.Team.objects.create(name="AwesomeCustomer2")
        # JOIN REQUEST user_3 => team_2
        join_request = account_models.Invitation.objects.create(
            team=self.team_2, email=self.user_3.email, invited_by=self.user_3
        )

        # JOIN REQUEST user_2 => team_1
        join_request = account_models.Invitation.objects.create(
            team=self.team_1, email=self.user_2.email, invited_by=self.user_2
        )

        self.user_5 = User.objects.create_user(
            username="test5", password="test", email="t5@test.com"
        )
        # INVITATION user_5 <= team_1
        invitation = account_models.Invitation.objects.create(
            team=self.team_1, email=self.user_5.email, invited_by=self.user_5
        )

    def test_join_request_create_accept(self):
        """
        user send a join request to a specific team
        """
        self.user_4 = User.objects.create_user(
            username="test4", password="test", email="t4@test.com"
        )
        response = self.client.post(
            reverse(
                "join_request-list",
            ),
            data={
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
                "email": self.user_4.email,
                "role": account_models.Membership.Role.ADMIN,
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_4),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get(
            reverse("invitation-accept", kwargs={"uuid": response.json()["uuid"]}),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertIn(self.user_4.id, list(self.team_1.members))

    def test_join_request_list_filter(self):
        response = self.client.get(
            reverse(
                "join_request-list",
            ),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_2),
        )
        self.assertEqual(response.json()["count"], 1)

        response = self.client.get(
            reverse(
                "join_request-list",
            ),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_3),
        )
        self.assertEqual(response.json()["count"], 2)


class UserTests(CoreTests):
    def setUp(self):
        super().setUp()
        self.token_str = self.get_token(self.user_1)

        self.token_obj = Token.objects.get(key=self.token_str)
        self.token_obj.created -= timezone.timedelta(
            seconds=settings.TOKEN_EXPIRED_AFTER_SECONDS + 10
        )
        self.token_obj.save()

    def test_register_user(self):
        response = self.client.post(
            reverse(
                "user-list",
            ),
            data={
                "username": "user_username",
                "password": "user_password",
                "password2": "user_password",
                "email": "user@netautomate.org",
                "first_name": "Kiavash",
                "last_name": "Ghamsari",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertNotEqual(User.objects.get(username="user_username"), None)

        # Fail: no first and last name
        response = self.client.post(
            reverse(
                "user-list",
            ),
            data={
                "username": "user_username2",
                "password": "user_password",
                "password2": "user_password",
                "email": "user2@netautomate.org",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Fail: wrong password2
        response = self.client.post(
            reverse(
                "user-list",
            ),
            data={
                "username": "user_username3",
                "password": "user_password",
                "password2": "user_password2",
                "email": "user2@netautomate.org",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Fail: no password2
        response = self.client.post(
            reverse(
                "user-list",
            ),
            data={
                "username": "user_username3",
                "password": "user_password",
                # "password2": "user_password2",
                "email": "user2@netautomate.org",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_expired_login_return_new_token(self):
        self.assertNotEqual(self.get_token(self.user_1), self.token_str)

    def test_expired_token(self):
        response = self.client.get(
            reverse(
                "team-list",
            ),
            follow=True,
            HTTP_AUTHORIZATION="Token {Token}".format(Token=self.token_str),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()["detail"], "Token has expired")


class AccountAPIKeyTests(CoreTests):
    def setUp(self):
        super().setUp()
        self.user_config_2_team_1 = self.make_user_configuration(
            self.team_1, prefix="2"
        )
        # api key name = "test_team_1_2"

        self.team_2 = account_models.Team.objects.create(name="AwesomeCustomer2")
        self.user_config_1_team_2 = self.make_user_configuration(self.team_2)
        # api key name = "test_team_2_"

    def test_duplicate_name_in_team_fails(self):
        """
        Api-key name can be the same as another team's api key name
        """
        response = self.client.post(
            reverse("apikey-list"),
            data={
                "name": "test_team_2_",
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        """
        Api-key name must be unique only in one team
        """
        response = self.client.post(
            reverse("apikey-list"),
            data={
                "name": f"test_{self.team_1.name}_2",
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_apikey_create_delete(self):
        response = self.client.post(
            reverse("apikey-list"),
            data={
                "name": "user_configuration",
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        new_config_user = User.objects.get(username="user_configuration")
        self.assertNotEqual(new_config_user, None)
        self.assertIn(
            new_config_user.pk,
            self.team_1.memberships.all().values_list("user", flat=True),
        )

        response = self.client.delete(
            reverse("apikey-detail", kwargs={"uuid": response.json()["uuid"]}),
            data={
                "name": "user_configuration",
                "team": reverse("team-detail", kwargs={"uuid": self.team_1.uuid}),
            },
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_filter(self):
        response = self.client.get(
            reverse("apikey-list"),
            follow=True,
            HTTP_AUTHORIZATION=self.get_token_header(self.user_1),
        )
        self.assertEqual(response.json()["count"], 2)
