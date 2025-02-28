"""Config flow for Volvo Connected Vehicle."""

import logging
from typing import Any

import jwt

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN


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
        self.logger.info("id_token: %s", id_token)
        decoced_id_token = jwt.decode(id_token, options={"verify_signature": False})
        await self.async_set_unique_id(decoced_id_token["sub"])
        if self.source != SOURCE_REAUTH:
            self._abort_if_unique_id_configured()

            access_token = data["token"]["access_token"]
            decoded_access_token = jwt.decode(
                access_token, options={"verify_signature": False}
            )

            return self.async_create_entry(
                title=decoded_access_token["userName"] or decoced_id_token["sub"],
                data=data,
            )

        return self.async_abort()
