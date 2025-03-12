"""Application credentials platform for the Volvo Connected Vehicle integration."""

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    AbstractOAuth2Implementation,
    LocalOAuth2ImplementationWithPkce,
)

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
) -> AbstractOAuth2Implementation:
    """Return auth implementation."""
    return VolvoAuthImplementation(
        hass,
        DOMAIN,
        credential,
        authorization_server=AuthorizationServer(
            authorize_url=OAUTH2_AUTHORIZE,
            token_url=OAUTH2_TOKEN,
        ),
    )


class VolvoAuthImplementation(LocalOAuth2ImplementationWithPkce):
    """VolvoAuthImplementation class."""

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
            authorization_server.authorize_url,
            authorization_server.token_url,
            credential.client_secret,
            code_verifier_length=100,
        )

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        data: dict = {
            "scope": " ".join(SCOPES),
        }
        data.update(super().extra_authorize_data)
        return data
