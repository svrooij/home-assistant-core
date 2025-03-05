"""Local OAuth2 implementation with PKCE for Volvo Connected Vehicle."""
# In my opinion, this code should be in core, but it's not there yet, see https://github.com/home-assistant/core/pull/139509.

import base64
import hashlib
from json import JSONDecodeError
import logging
import secrets
from typing import Any, cast

from aiohttp import ClientError
import jwt
from yarl import URL

from homeassistant.components import http
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.config_entry_oauth2_flow import (
    AUTH_CALLBACK_PATH,
    DATA_JWT_SECRET,
    HEADER_FRONTEND_BASE,
    MY_AUTH_CALLBACK_PATH,
    AbstractOAuth2Implementation,
    async_get_clientsession,
)

_LOGGER = logging.getLogger(__name__)


class LocalOAuthWithPkce(AbstractOAuth2Implementation):
    """Local OAuth2 implementation."""

    def __init__(
        self,
        hass: HomeAssistant,
        domain: str,
        client_id: str,
        client_secret: str,
        authorize_url: str,
        token_url: str,
    ) -> None:
        """Initialize local auth implementation."""
        self.hass = hass
        self._domain = domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_url = authorize_url
        self.token_url = token_url

    @property
    def name(self) -> str:
        """Name of the implementation."""
        return "LocalOAuthWithPkce"

    @property
    def domain(self) -> str:
        """Domain providing the implementation."""
        return self._domain

    @property
    def redirect_uri(self) -> str:
        """Return the redirect uri."""
        if "my" in self.hass.config.components:
            return MY_AUTH_CALLBACK_PATH

        if (req := http.current_request.get()) is None:
            raise RuntimeError("No current request in context")

        if (ha_host := req.headers.get(HEADER_FRONTEND_BASE)) is None:
            raise RuntimeError("No header in request")

        return f"{ha_host}{AUTH_CALLBACK_PATH}"

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {}

    @property
    def extra_token_data(self) -> dict:
        """Extra data that needs to be added to the token request."""
        return {}

    async def async_generate_authorize_url(self, flow_id: str) -> str:
        """Generate a url for the user to authorize."""
        redirect_uri = self.redirect_uri
        return str(
            URL(self.authorize_url)
            .with_query(
                {
                    "response_type": "code",
                    "client_id": self.client_id,
                    "redirect_uri": redirect_uri,
                    "state": _encode_jwt(
                        self.hass,
                        {
                            "flow_id": flow_id,
                            "redirect_uri": redirect_uri,
                        },
                    ),
                }
            )
            .update_query(self.extra_authorize_data)
        )

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Resolve the authorization code to tokens."""
        data: dict = {
            "grant_type": "authorization_code",
            "code": external_data["code"],
            "redirect_uri": external_data["state"]["redirect_uri"],
        }
        data.update(self.extra_token_data)
        return await self._token_request(data)

    async def _async_refresh_token(self, token: dict) -> dict:
        """Refresh tokens."""
        new_token = await self._token_request(
            {
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "refresh_token": token["refresh_token"],
            }
        )
        return {**token, **new_token}

    async def _token_request(self, data: dict) -> dict:
        """Make a token request."""
        session = async_get_clientsession(self.hass)

        data["client_id"] = self.client_id

        if self.client_secret:
            data["client_secret"] = self.client_secret

        _LOGGER.debug("Sending token request to %s", self.token_url)
        resp = await session.post(self.token_url, data=data)
        if resp.status >= 400:
            try:
                error_response = await resp.json()
            except (ClientError, JSONDecodeError):
                error_response = {}
            error_code = error_response.get("error", "unknown")
            error_description = error_response.get("error_description", "unknown error")
            _LOGGER.error(
                "Token request for %s failed (%s): %s",
                self.domain,
                error_code,
                error_description,
            )
        resp.raise_for_status()
        return cast(dict, await resp.json())

    @staticmethod
    def generate_code_verifier(code_verifier_length: int = 128) -> str:
        """Generate a code verifier."""
        if not 43 <= code_verifier_length <= 128:
            msg = "Parameter `code_verifier_length` must verify `43 <= code_verifier_length <= 128`."
            raise ValueError(msg)
        return secrets.token_urlsafe(96)[:code_verifier_length]

    @staticmethod
    def compute_code_challenge(code_verifier: str) -> str:
        """Compute the code challenge."""
        if not 43 <= len(code_verifier) <= 128:
            msg = "Parameter `code_verifier` must verify `43 <= len(code_verifier) <= 128`."
            raise ValueError(msg)

        hashed = hashlib.sha256(code_verifier.encode("ascii")).digest()
        encoded = base64.urlsafe_b64encode(hashed)
        return encoded.decode("ascii").replace("=", "")


@callback
def _encode_jwt(hass: HomeAssistant, data: dict) -> str:
    """JWT encode data."""
    if (secret := hass.data.get(DATA_JWT_SECRET)) is None:
        secret = hass.data[DATA_JWT_SECRET] = secrets.token_hex()

    return jwt.encode(data, secret, algorithm="HS256")
