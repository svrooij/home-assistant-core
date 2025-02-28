"""Define the Volvo Connected Vehicle API coordinator."""

from dataclasses import dataclass
from typing import Any

from kiota_abstractions.authentication import AccessTokenProvider, AllowedHostsValidator
from kiota_http.httpx_request_adapter import HttpxRequestAdapter
from volvo_connected import VolvoAuthenticationProvider, VolvoConnectedClient
from volvo_connected.vcclient.models.resource_instance_float import (
    ResourceInstanceFloat,
)
from volvo_connected.vcclient.models.resource_instance_integer import (
    ResourceInstanceInteger,
)
from volvo_connected.vcclient.models.vehicle_details_data import VehicleDetails_data

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
    timedelta,
)

from .const import DOMAIN, LOGGER

type VolvoConfigEntry = ConfigEntry[VolvoCoordinator]


@dataclass
class VolvoUpdate:
    """Class for holding Volvo data."""

    vin: str
    model: str | None
    battery_charge_level: ResourceInstanceFloat | None = None
    distance_to_empty_battery: ResourceInstanceInteger | None = None
    fuel_amount: ResourceInstanceFloat | None = None


class VolvoHaAccessTokenProvider(AccessTokenProvider):
    """Provide Volvo Connected Vehicle authentication tied to an OAuth2 based config entry."""

    def __init__(
        self,
        # websession: ClientSession,
        oauth_session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize Volvo Connected Vehicle auth."""
        # super().__init__(websession)
        self._oauth_session = oauth_session

    async def get_authorization_token(
        self, uri: str, additional_authentication_context: dict[str, Any] | None = None
    ) -> str:
        """Return a valid access token."""
        await self._oauth_session.async_ensure_token_valid()

        return self._oauth_session.token["access_token"]

    def get_allowed_hosts_validator(self) -> AllowedHostsValidator:
        """Get the allowed hosts validator."""
        return AllowedHostsValidator()


class VolvoCoordinator(DataUpdateCoordinator[dict[str, VolvoUpdate]]):
    """Class to manage fetching Volvo data."""

    config_entry: VolvoConfigEntry
    _vehicles: list[VehicleDetails_data] = []

    def __init__(
        self,
        hass: HomeAssistant,
        session: config_entry_oauth2_flow.OAuth2Session,
        entry: VolvoConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        self.config_entry = entry
        self.vcc = VolvoConnectedClient(
            HttpxRequestAdapter(
                VolvoAuthenticationProvider(
                    "294137f4b70b460b999794ec5d1180fa",  # TODO: Get this from somewhere, instead of hardcoding it (VCC key tied to application credentials)
                    VolvoHaAccessTokenProvider(session),
                )
            )
        )
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=15),
        )

    async def _async_update_data(self) -> dict[str, VolvoUpdate]:
        """Update data via library."""
        try:
            # Get data from library
            # Should this be done more often?
            # Do we want this to be configureable?
            if not self._vehicles:
                vehiclesResult = await self.vcc.vehicles.get()
                for vehicle in vehiclesResult.data:
                    vehicleDetails = await self.vcc.vehicles.by_vin(vehicle.vin).get()
                    self._vehicles.append(vehicleDetails.data)

            newData: dict[str, VolvoUpdate] = {}
            for vehicle in self._vehicles:
                # TODO Load additional data
                fuel = await self.vcc.vehicles.by_vin(vehicle.vin).fuel.get()
                statistics = await self.vcc.vehicles.by_vin(
                    vehicle.vin
                ).statistics.get()
                newData[vehicle.vin] = VolvoUpdate(
                    vin=vehicle.vin,
                    model=vehicle.descriptions.model,
                    battery_charge_level=fuel.data.battery_charge_level,
                    distance_to_empty_battery=statistics.data.distance_to_empty_battery,
                    fuel_amount=fuel.data.fuel_amount,
                )

            return newData

        except Exception as error:  # pylint: disable=broad-except
            raise UpdateFailed(f"Error communicating with API: {error}") from error
