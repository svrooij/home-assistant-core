"""Support for Proxmox VE."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
import homeassistant.helpers.config_validation as cv

from .const import (
    _LOGGER,
    CONF_CONTAINERS,
    CONF_NODE,
    CONF_NODES,
    CONF_REALM,
    CONF_VMS,
    DEFAULT_PORT,
    DEFAULT_REALM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)
from .coordinator import ProxmoxConfigEntry, ProxmoxDataUpdateCoordinator

PLATFORMS = [Platform.BINARY_SENSOR]

CONFIG_SCHEMA_NODE = vol.Schema(
    {
        vol.Required(CONF_HOST): cv.string,
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
        vol.Optional(CONF_REALM, default=DEFAULT_REALM): cv.string,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Required(CONF_NODES): vol.All(
            cv.ensure_list,
            [
                vol.Schema(
                    {
                        vol.Required(CONF_NODE): cv.string,
                        vol.Optional(CONF_VMS, default=[]): [cv.positive_int],
                        vol.Optional(CONF_CONTAINERS, default=[]): [cv.positive_int],
                    }
                )
            ],
        ),
    }
)
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                CONFIG_SCHEMA_NODE,
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup_entry(hass: HomeAssistant, entry: ProxmoxConfigEntry) -> bool:
    """Set up the Proxmox VE component."""

    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)
    entry.coordinator = ProxmoxDataUpdateCoordinator(
        hass, entry.title, dict(entry.data)
    )

    # await hass.async_create_task(entry.coordinator.configure_client())
    # coordinator = ProxmoxDataUpdateCoordinator(hass, entry.title, dict(entry.data))
    await entry.coordinator.async_config_entry_first_refresh()
    # entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.BINARY_SENSOR, Platform.SELECT, Platform.SENSOR]
    )
    return True
