"""Configuration stuff for Proxmox VE."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)

from .const import (
    CONF_CONTAINERS,
    CONF_NODE,
    CONF_NODES,
    CONF_REALM,
    CONF_TOKEN_ID,
    CONF_VMS,
    DEFAULT_PORT,
    DEFAULT_REALM,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

CONF_ADDITIONAL_NODE = "additional_node"

SCHEMA_HOST = vol.Schema(
    {
        vol.Required(CONF_HOST, default="192.168.200.28"): str,
        vol.Required(CONF_USERNAME, default="hass"): str,
        vol.Optional(CONF_REALM, default=DEFAULT_REALM): str,
        vol.Required(CONF_TOKEN): str,
        vol.Required(CONF_TOKEN_ID, default="hass-api"): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    },
    extra=vol.ALLOW_EXTRA,
)

SCHEMA_NODE = vol.Schema(
    {
        vol.Required(CONF_NODE, default="proxmox"): str,
        vol.Optional(CONF_VMS, default="100"): str,
        vol.Optional(CONF_CONTAINERS, default="101,103"): str,
        vol.Optional(CONF_ADDITIONAL_NODE, default=False): bool,
    }
)


class ProxmoxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Proxmox VE config flow."""

    VERSION = 1
    MINOR_VERSION = 0

    _data: Mapping[str, Any] | None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow start."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self._data = user_input
            self._data[CONF_NODES] = []
            return await self.async_step_node()
        return self.async_show_form(
            step_id="user", data_schema=SCHEMA_HOST, errors=errors
        )

    async def async_step_node(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle adding a node."""
        errors: dict[str, str] = {}
        if user_input is not None:
            # validate that we have at least one VM or container
            if not user_input[CONF_VMS] and not user_input[CONF_CONTAINERS]:
                errors["base"] = "no_vms_or_containers"
            else:
                self._data[CONF_NODES].append(
                    {
                        CONF_NODE: user_input[CONF_NODE],
                        CONF_VMS: [
                            int(x) for x in ((user_input[CONF_VMS] or "").split(","))
                        ],
                        CONF_CONTAINERS: [
                            int(x)
                            for x in ((user_input[CONF_CONTAINERS] or "").split(","))
                        ],
                    }
                )

            if not errors and self._data:
                if user_input[CONF_ADDITIONAL_NODE]:
                    return await self.async_step_node()
                return self.async_create_entry(
                    title=f"{self._data[CONF_HOST]}:{self._data[CONF_PORT]}",
                    data=self._data,
                )

        return self.async_show_form(
            step_id="node", data_schema=SCHEMA_NODE, errors=errors
        )
