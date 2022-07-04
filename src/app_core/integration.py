import json
import requests
from rest_framework import status


class ServiceProvider:
    class AuthMethods:
        JWT = 'JWT'
        PASSWORD = 'PASSWORD'
        API_KEY = 'API_KEY'
        SSH_KEY = 'SSH_KEY'
        AuthMethodsCHOICES = (
            (JWT, 'JWT'),
            (PASSWORD, 'PASSWORD'),
            (API_KEY, 'API_KEY'),
            (SSH_KEY, 'SSH_KEY'),
        )

    def __init__(
            self,
            host='',
            auth_url='',
            auth_type=AuthMethods.PASSWORD,
            credentials={},
            options={},
    ):
        self.host = host
        self.auth_url = auth_url
        self.auth_type = auth_type
        self.credentials = credentials
        self.options = options

        self.token = {}

    def login_jwt(self):
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        response = session.post(
            self.auth_url,
            data=json.dumps(self.credentials),
            timeout=60,
            verify=False,
        )
        if response.status_code != status.HTTP_200_OK:
            raise Exception("Auth Exception")

        data = response.json()
        self.token.update({'token': data.get('token', None)})

    def login_password(self):
        return NotImplementedError

    def login(self):
        if self.auth_type == self.AuthMethods.JWT:
            self.login_jwt()
        elif self.auth_type == self.AuthMethods.PASSWORD:
            self.login_password()

    def request_header_creator_jwt(self):
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': 'Bearer {}'.format(self.token.get('token', ''))
        })
        return session

    def request_header_creator_api_key(self):
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            # 'Authorization': 'Bearer {}'.format(self.token.get('token', '')),
            'Authorization': 'Api-Key {API_KEY}'.format(API_KEY=self.credentials.get('API_KEY'))
        })
        return session

    def request_header_creator(self):
        if self.auth_type == self.AuthMethods.JWT:
            return self.request_header_creator_jwt()
        if self.auth_type == self.AuthMethods.API_KEY:
            return self.request_header_creator_api_key()
