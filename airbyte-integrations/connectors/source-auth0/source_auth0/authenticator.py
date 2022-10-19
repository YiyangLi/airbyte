#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#

from typing import Any, Mapping, Tuple

from urllib import parse
from airbyte_cdk.sources.streams.http.requests_native_auth import Oauth2Authenticator

class Auth0Oauth2Authenticator(Oauth2Authenticator):
    def __init__(self, base_url: str, audience: str, **kwargs):
        super().__init__(**kwargs)
        self.token_refresh_endpoint = parse.urljoin(base_url, f"/oauth/token")
        self.audience = audience.rstrip("/") + "/"

    def build_refresh_request_body(self) -> Mapping[str, Any]:
        if not self.get_refresh_token():
          return {
              "grant_type": "client_credentials",
              "client_id": self.get_client_id(),
              "client_secret": self.get_client_secret(),
              "audience": self.audience,
          }
        else:
          return super().build_refresh_request_body()
