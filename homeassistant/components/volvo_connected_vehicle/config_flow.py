"""Config flow for Volvo Connected Vehicle."""

import base64
import hashlib
import logging
from typing import Any

import jwt

from homeassistant.config_entries import ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN


def _hash_string_urlsafe(stringToHash: str) -> str:
    """Hash a string in a URL safe way."""

    hashed = hashlib.sha256(stringToHash.encode("ascii")).digest()
    encoded = base64.urlsafe_b64encode(hashed)
    return encoded.decode("ascii").replace("=", "")


class OAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Volvo Connected Vehicle OAuth2 authentication."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    async def async_oauth_create_entry(
        self,
        data: dict[str, Any],
    ) -> ConfigFlowResult:
        """Handle the initial step."""

        self.logger.debug("async_oauth_create_entry: %s", data)

        # setting the unique id based on the sub claim in the id_token
        id_token = data["token"]["id_token"]
        # not sure if you want the ID token in the logs
        self.logger.debug("id_token: %s", id_token)
        decoced_id_token = jwt.decode(id_token, options={"verify_signature": False})
        # Using the sub claim as the unique id, but hashing it to avoid potential privacy issues
        await self.async_set_unique_id(_hash_string_urlsafe(decoced_id_token["sub"]))

        # if self.source != SOURCE_REAUTH:
        self._abort_if_unique_id_configured()

        access_token = data["token"]["access_token"]
        decoded_access_token = jwt.decode(
            access_token, options={"verify_signature": False}
        )

        # I think users want to see their username in the UI, so we use the username if it exists
        # it is however recommended to threat the access token as opaque and not decode it
        # but the username is not in the id_token (bummer)
        return self.async_create_entry(
            title=decoded_access_token["userName"] or decoced_id_token["sub"],
            data=data,
        )

        # return self.async_abort()
