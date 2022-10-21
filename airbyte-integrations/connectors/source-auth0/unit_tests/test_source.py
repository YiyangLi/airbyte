#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from unittest.mock import MagicMock

from source_auth0.authenticator import Auth0Oauth2Authenticator
from source_auth0.source import (
    SourceAuth0,
    initialize_authenticator
)
class TestAuthentication:
    def test_check_connection_ok(self, requests_mock, oauth_config, api_url):
        oauth_authentication_instance = initialize_authenticator(config=oauth_config)
        assert isinstance(oauth_authentication_instance, Auth0Oauth2Authenticator)

        source_auth0 = SourceAuth0()
        requests_mock.get(f"{api_url}/api/v2/users?per_page=1", json={"connect": "ok"})
        requests_mock.post(f"{api_url}/oauth/token", json={"access_token": "test_token", "expires_in": 948})
        assert source_auth0.check_connection(logger=MagicMock(), config=oauth_config) == (True, None)

# def test_check_connection(mocker):
#     source = SourceAuth0()
#     logger_mock, config_mock = MagicMock(), MagicMock()
#     assert source.check_connection(logger_mock, config_mock) == (True, None)


# def test_streams(mocker):
#     source = SourceAuth0()
#     config_mock = MagicMock()
#     streams = source.streams(config_mock)
#     # TODO: replace this with your streams number
#     expected_streams_number = 2
#     assert len(streams) == expected_streams_number
