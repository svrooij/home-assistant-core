"""Configuration for Volvo Connected Vehicle tests."""

import pytest
import respx

from homeassistant.components.application_credentials import (
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.components.volvo_connected_vehicle.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from .const import (
    ACCESS_TOKEN,
    API_BASE_ADDRESS,
    CLIENT_ID,
    CLIENT_SECRET,
    EXPIRES_AT,
    ID_TOKEN,
)

from tests.common import MockConfigEntry, load_fixture


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Mock a config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Volvo Connected Vehicle fake",
        data={
            "token": {
                "access_token": ACCESS_TOKEN,
                "id_token": ID_TOKEN,
                "expires_at": EXPIRES_AT,
            },
            "auth_implementation": "volvo_connected_vehicle",
        },
        options={},
    )


@pytest.fixture
async def setup_credentials(hass: HomeAssistant) -> None:
    """Fixture to setup credentials."""
    assert await async_setup_component(hass, "application_credentials", {})
    await async_import_client_credential(
        hass,
        DOMAIN,
        ClientCredential(CLIENT_ID, CLIENT_SECRET),
    )


@pytest.fixture
def mock_volvo_api(hass: HomeAssistant) -> None:
    """Mock used volvo endpoints."""

    respx.get(f"{API_BASE_ADDRESS}/vehicles").respond(
        status_code=200,
        json=load_fixture("get_vehicles.json", integration="volvo_connected_vehicle"),
    )

    respx.get(f"{API_BASE_ADDRESS}/vehicles/VIN123").respond(
        status_code=200,
        json=load_fixture(
            "get_vehicle_vin123.json", integration="volvo_connected_vehicle"
        ),
    )

    respx.get(f"{API_BASE_ADDRESS}/vehicles/VIN123/fuel").respond(
        status_code=200,
        json=load_fixture(
            "get_fuel_vin123.json", integration="volvo_connected_vehicle"
        ),
    )

    respx.get(f"{API_BASE_ADDRESS}/vehicles/VIN123/statistics").respond(
        status_code=200,
        json=load_fixture(
            "get_statistics_vin123.json", integration="volvo_connected_vehicle"
        ),
    )
