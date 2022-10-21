#
# Copyright (c) 2022 Airbyte, Inc., all rights reserved.
#


import logging
from abc import ABC, abstractmethod
from typing import Any, Iterable, List, Mapping, MutableMapping, Optional, Tuple
from urllib import parse

import pendulum
import requests
from airbyte_cdk.sources import AbstractSource
from airbyte_cdk.sources.streams import Stream
from airbyte_cdk.sources.streams.http import HttpStream
from source_auth0.utils import datetime_to_string, get_api_endpoint, initialize_authenticator


# Basic full refresh stream
class Auth0Stream(HttpStream, ABC):
    api_version = "v2"
    page_size = 50
    resource_name = "entities"

    def __init__(self, url_base: str, **kwargs):
        super().__init__(**kwargs)
        self.api_endpoint = get_api_endpoint(url_base, self.api_version)

    def path(self, **kwargs) -> str:
        return self.resource_name

    @property
    def url_base(self) -> str:
        return self.api_endpoint

    def next_page_token(self, response: requests.Response) -> Optional[Mapping[str, Any]]:
        body = response.json()
        if "start" in body and "limit" in body and "length" in body and "total" in body:
            try:
                start = int(body["start"])
                limit = int(body["limit"])
                length = int(body["length"])
                total = int(body["total"])
                current = start // limit
                if length < limit or (start + length) == total:
                    return None
                else:
                    return {
                        "page": current + 1,
                        "per_page": limit,
                    }
            except Exception:
                return None
        return None

    def request_params(
        self, stream_state: Mapping[str, Any], stream_slice: Mapping[str, any] = None, next_page_token: Mapping[str, Any] = None
    ) -> MutableMapping[str, Any]:
        return {
            "page": 0,
            "per_page": self.page_size,
            "include_totals": "true",
            **(next_page_token or {}),
        }

    def parse_response(self, response: requests.Response, **kwargs) -> Iterable[Mapping]:
        print(response.json())
        yield from response.json().get(self.resource_name)

    def backoff_time(self, response: requests.Response) -> Optional[float]:
        # The rate limit resets on the timestamp indicated
        # https://auth0.com/docs/troubleshoot/customer-support/operational-policies/rate-limit-policy/management-api-endpoint-rate-limits
        if response.status_code == requests.codes.TOO_MANY_REQUESTS:
            next_reset_epoch = int(response.headers["x-ratelimit-reset"])
            next_reset = pendulum.from_timestamp(next_reset_epoch)
            next_reset_duration = pendulum.now("UTC").diff(next_reset)
            return next_reset_duration.seconds


# Basic incremental stream
class IncrementalAuth0Stream(Auth0Stream, ABC):
    min_id = ""

    @property
    @abstractmethod
    def cursor_field(self) -> str:
        pass

    def get_updated_state(self, current_stream_state: MutableMapping[str, Any], latest_record: Mapping[str, Any]) -> Mapping[str, Any]:
        min_cursor_value = self.min_id if self.min_id else datetime_to_string(pendulum.DateTime.min)
        print(self.cursor_field)
        return {
            self.cursor_field: max(
                latest_record.get(self.cursor_field, min_cursor_value),
                current_stream_state.get(self.cursor_field, min_cursor_value),
            )
        }

    def request_params(
        self,
        stream_state: Mapping[str, Any],
        stream_slice: Mapping[str, any] = None,
        next_page_token: Mapping[str, Any] = None,
    ) -> MutableMapping[str, Any]:
        params = super().request_params(stream_state, stream_slice, next_page_token)
        # cursor_field:1 means acending, cursor_field:-1 means decending
        filter_param = {"sort": f"{self.cursor_field}:1"}
        params.update(filter_param)
        return params


class Users(IncrementalAuth0Stream):
    min_id = datetime_to_string(pendulum.DateTime.min)
    primary_key = "user_id"
    resource_name = "users"
    cursor_field = "updated_at"


# Source
class SourceAuth0(AbstractSource):
    def check_connection(self, logger: logging.Logger, config: Mapping[str, Any]) -> Tuple[bool, any]:
        try:
            auth = initialize_authenticator(config)
            api_endpoint = get_api_endpoint(config.get("base_url"), "v2")
            url = parse.urljoin(api_endpoint, "users")
            response = requests.get(
                url,
                params={"per_page": 1},
                headers=auth.get_auth_header(),
            )

            if response.status_code == requests.codes.ok:
                return True, None

            return False, response.json()
        except Exception:

            return False, "Failed to authenticate with the provided credentials"

    def streams(self, config: Mapping[str, Any]) -> List[Stream]:
        initialization_params = {"authenticator": initialize_authenticator(config), "url_base": config.get("base_url")}
        return [Users(**initialization_params)]
