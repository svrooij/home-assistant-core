"""Local OAuth2 implementation with PKCE for Volvo Connected Vehicle."""
# In my opinion, this code should be in core, but it's not there yet, see https://github.com/home-assistant/core/pull/139509.

import base64
import hashlib
import logging
import secrets
from typing import Any

from homeassistant.helpers.config_entry_oauth2_flow import LocalOAuth2Implementation

_LOGGER = logging.getLogger(__name__)


class LocalOAuthWithPkce(LocalOAuth2Implementation):
    """Local OAuth2 implementation."""

    @property
    def domain(self) -> str:
        """Domain providing the implementation."""
        return self._domain

    @property
    def extra_token_data(self) -> dict:
        """Extra data that needs to be added to the token request."""
        return {}

    async def async_resolve_external_data(self, external_data: Any) -> dict:
        """Resolve the authorization code to tokens."""
        data: dict = {
            "grant_type": "authorization_code",
            "code": external_data["code"],
            "redirect_uri": external_data["state"]["redirect_uri"],
        }
        data.update(self.extra_token_data)
        return await self._token_request(data)

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
