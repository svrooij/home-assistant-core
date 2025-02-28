"""Application credentials platform for the Volvo Connected Vehicle integration."""

import base64
import hashlib
import os
import re

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import DOMAIN, OAUTH2_AUTHORIZE, OAUTH2_TOKEN

# Scopes required by the integration
# openid is required by the OAuth2 flow
# conve:vehicle_relation is required to get the vehicles that belong to the user
# conve:fuel_status is required to get the fuel status of the vehicle
# conve:battery_charge_level is required to get the battery charge level of the vehicle
# conve:trip_statistics is required to get the trip statistics of the vehicle (like distance to empty battery)
SCOPES = [
    "openid",
    "conve:vehicle_relation",
    "conve:fuel_status",
    "conve:battery_charge_level",
    "conve:trip_statistics",
]


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> config_entry_oauth2_flow.AbstractOAuth2Implementation:
    """Return auth implementation."""
    return OAuth2WithPKCEImplementation(
        hass,
        DOMAIN,
        credential,
        authorization_server=AuthorizationServer(
            authorize_url=OAUTH2_AUTHORIZE,
            token_url=OAUTH2_TOKEN,
        ),
    )


def _generateCodeChallengePair() -> tuple:
    # code_verifier = secrets.token_urlsafe(128).decode('utf-8')
    code_verifier = base64.urlsafe_b64encode(os.urandom(128)).decode("utf-8")
    code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
    code_verifier = code_verifier[
        :100
    ]  # 'code_verifier must be between 43 and 128 characters.'

    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("utf-8")).digest()
    ).decode("utf-8")
    code_challenge = code_challenge.replace("=", "")

    return (code_verifier, code_challenge)


class OAuth2WithPKCEImplementation(config_entry_oauth2_flow.LocalOAuth2Implementation):
    """Application Credentials local oauth2 with PKCE implementation."""

    code_verifier: str
    code_challenge: str

    def __init__(
        self,
        hass: HomeAssistant,
        auth_domain: str,
        credential: ClientCredential,
        authorization_server: AuthorizationServer,
    ) -> None:
        """Initialize AuthImplementation."""
        super().__init__(
            hass,
            auth_domain,
            credential.client_id,
            credential.client_secret,
            authorization_server.authorize_url,
            authorization_server.token_url,
        )
        self._name = credential.name
        # Init PKCE
        self.code_verifier, self.code_challenge = _generateCodeChallengePair()

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return {
            "scope": " ".join(SCOPES),
            "code_challenge_method": "S256",
            "code_challenge": self.code_challenge,  # PKCE
        }

    @property
    def extra_token_data(self) -> dict:
        """Extra data that needs to be appended to the token request."""
        return {
            "code_verifier": self.code_verifier,
        }
