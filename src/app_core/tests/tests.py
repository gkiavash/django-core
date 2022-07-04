import json
import os

import requests_mock
from django.test import TestCase
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework_api_key.models import APIKey

from app_account import models

User = get_user_model()


from django.test.runner import DiscoverRunner


class NoDbTestRunner(DiscoverRunner):
    """A test runner to test without database creation"""

    def setup_databases(self, **kwargs):
        """Override the database creation defined in parent class"""
        pass

    def teardown_databases(self, old_config, **kwargs):
        """Override the database teardown defined in parent class"""
        pass


def ensure_mock(func, **kwargs_):
    def decorator_(*args, **kwargs):
        with requests_mock.Mocker() as m:
            m.register_uri(
                'POST',
                'url_negotiation_create',
                json={'id': 1},
                status_code=201
            )
            m.register_uri(
                'POST',
                'auth_url',
                json={'token': 1},
                status_code=200
            )
            return func(*args, **kwargs)

    return decorator_


class CoreTests(APITestCase):

    def setUp(self):
        super().setUp()
        self.username = 'test'
        self.password = 'test'
        self.user = User.objects.create_user(username=self.username, password=self.password)
        self.api_key, self.key = models.UserAPIKey.objects.create_key(name="test key", user=self.user)

    def ensure_auth(self, user):
        response = self.client.post(
            reverse('rest_framework:login',),
            data={
                'username': user.username,
                'password': 'test',
            },
            follow=True,
        )
        return response.status_code

    def get_token(self, user):
        response = self.client.post(
            reverse('auth-login',),
            data={
                'username': user.username,
                'password': 'test',
            },
            follow=True,
        )
        return response.json().get('token')

    def get_token_header(self, user):
        return f'Token {self.get_token(user)}'

    def get_apikey_header(self, key=None):
        if key is None:
            return 'Api-Key {API_KEY}'.format(API_KEY=self.key)
        return 'Api-Key {API_KEY}'.format(API_KEY=key)
