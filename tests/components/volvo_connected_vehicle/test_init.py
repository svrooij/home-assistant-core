"""Test the Home Assistant volvo connected car module."""

from __future__ import annotations

import respx

from homeassistant.components.volvo_connected_vehicle.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


@respx.mock
async def test_load_unload_entry(
    hass: HomeAssistant,
    setup_credentials,
    mock_volvo_api,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test load and unload entry."""
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)

    entry = hass.config_entries.async_entries(DOMAIN)[0]

    assert entry.state is ConfigEntryState.LOADED

    await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
