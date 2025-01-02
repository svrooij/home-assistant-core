"""Data update coordinator for the Proximity integration."""

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from pyproxmox_ve import ProxmoxVEAPI
from pyproxmox_ve.exceptions import (
    ProxmoxAPIAuthenticationError,
    ProxmoxAPIJSONKeyError,
    ProxmoxAPIResponseError,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PORT,
    CONF_TOKEN,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, State
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import (
    _LOGGER,
    COMMAND_REBOOT,
    COMMAND_RESET,
    COMMAND_RESUME,
    COMMAND_SHUTDOWN,
    COMMAND_START,
    COMMAND_STOP,
    COMMAND_SUSPEND,
    CONF_CONTAINERS,
    CONF_NODE,
    CONF_NODES,
    CONF_REALM,
    CONF_TOKEN_ID,
    CONF_VMS,
    DEFAULT_PORT,
    UPDATE_INTERVAL,
)

type ProxmoxConfigEntry = ConfigEntry[ProxmoxDataUpdateCoordinator]


@dataclass
class StateChangedData:
    """StateChangedData class."""

    entity_id: str
    old_state: State | None
    new_state: State | None


@dataclass
class ProxmoxContainerData:
    """ProxmoxContainerData class."""

    cpu: float | None
    cpus: int | None
    memory: float | None
    memory_usage: float | None
    name: str | None
    running: bool


@dataclass
class ProxmoxVmData:
    """ProxmoxVmData class."""

    cpu: float | None
    cpus: int | None
    memory: float | None
    memory_usage: float | None
    name: str | None
    running: bool
    agent_running: bool


@dataclass
class ProxmoxNodeData:
    """ProxmoxNodeData class."""

    containers: dict[int, ProxmoxContainerData]
    vms: dict[int, ProxmoxVmData]


@dataclass
class ProxmoxData(dict[str, Any]):
    """ProximityCoordinatorData class."""

    nodes: dict[str, ProxmoxNodeData]


DEFAULT_PROXMOX_DATA = ProxmoxData({})


class ProxmoxDataUpdateCoordinator(DataUpdateCoordinator[ProxmoxData]):
    """Proximity data update coordinator."""

    _entry_configuration: dict[str, Any]
    _client: ProxmoxVEAPI | None
    version: str | None

    def __init__(
        self, hass: HomeAssistant, friendly_name: str, config: dict[str, Any]
    ) -> None:
        """Initialize the Proxmox coordinator."""
        self._entry_configuration = config

        super().__init__(
            hass,
            _LOGGER,
            name=friendly_name,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

        self.data = DEFAULT_PROXMOX_DATA

        self.state_change_data: StateChangedData | None = None

    async def _async_setup(self):
        """Set up the Proxmox coordinator."""
        await self.configure_client()
        return await super()._async_setup()

    async def configure_client(self) -> None:
        """Configure the Proxmox client."""
        try:
            user: str = self._entry_configuration[CONF_USERNAME]
            if "@" not in user:
                user = f"{user}@{self._entry_configuration[CONF_REALM]}"
            self._client = ProxmoxVEAPI(
                url=f"https://{self._entry_configuration[CONF_HOST]}:{self._entry_configuration.get(CONF_PORT, DEFAULT_PORT)}/",
                username=user,
                api_token=self._entry_configuration[CONF_TOKEN],
                api_token_id=self._entry_configuration[CONF_TOKEN_ID],
                verify_ssl=self._entry_configuration[CONF_VERIFY_SSL],
            )
            self.version = (await self._client.version.get_version())["version"]
        except ProxmoxAPIAuthenticationError as e:
            _LOGGER.error("Error authenticating with Proxmox: %s", e)
            raise

    async def _async_update_data(self):
        # if self._client is None:
        #     await self.configure_client()
        new_data = DEFAULT_PROXMOX_DATA
        for node in self._entry_configuration[CONF_NODES]:
            k = node[CONF_NODE]
            try:
                new_data.nodes[k] = await self._async_get_node_data(k, node)
            except ProxmoxAPIJSONKeyError as e:
                _LOGGER.error("Error fetching node data: %s", e)
                continue
        return new_data

    async def _async_get_node_data(
        self, nodeName: str, node: dict[str, Any]
    ) -> ProxmoxNodeData | None:
        """Fetch the data for a node."""

        containers = {}
        vms = {}
        for containerId in node[CONF_CONTAINERS]:
            try:
                containers[containerId] = await self._async_get_container_data(
                    nodeName, containerId
                )
            except ProxmoxAPIJSONKeyError as e:
                _LOGGER.error("Error fetching container data: %s", e)
                continue

        for vmId in node[CONF_VMS]:
            try:
                vms[vmId] = await self._async_get_vm_data(nodeName, vmId)
            except ProxmoxAPIJSONKeyError as e:
                _LOGGER.error("Error fetching container data: %s", e)
                continue

        return ProxmoxNodeData(containers, vms)

    async def _async_get_container_data(
        self, nodeName: str, containerId: int
    ) -> ProxmoxContainerData:
        """Fetch the data for a container."""
        if self._client is None:
            raise ProxmoxAPIResponseError("Client not configured")
        container = await self._client.nodes(nodeName).lxc(containerId).get_status()
        return ProxmoxContainerData(
            container["cpu"],
            container["cpus"],
            container["maxmem"],
            container["mem"],
            container["name"],
            container["status"] == "running",
        )

    async def _async_get_vm_data(self, nodeName: str, vmId: int) -> ProxmoxVmData:
        """Fetch the data for a vm."""
        if self._client is None:
            raise ProxmoxAPIResponseError("Client not configured")
        vm = await self._client.nodes(nodeName).qemu(vmId).get_status()
        return ProxmoxVmData(
            vm["cpu"],
            vm["cpus"],
            vm["maxmem"],
            vm["mem"],
            vm["name"],
            vm["status"] == "running",
            vm["agent"] == 1,
        )

    async def async_send_qemu_command(
        self, nodeName: str, vmId: int, command: str
    ) -> None:
        """Send a command to a vm."""
        endpoint = self._client.nodes(nodeName).qemu(vmId)
        try:
            if command == COMMAND_START:
                await endpoint.start()
            elif command == COMMAND_STOP:
                await endpoint.stop()
            elif command == COMMAND_REBOOT:
                await endpoint.reboot()
            elif command == COMMAND_RESET:
                await endpoint.reset()
            elif command == COMMAND_SHUTDOWN:
                await endpoint.shutdown()
            elif command == COMMAND_SUSPEND:
                await endpoint.suspend()
            elif command == COMMAND_RESUME:
                await endpoint.resume()
            else:
                _LOGGER.error("Unknown command %s", command)
        except ProxmoxAPIResponseError as e:
            _LOGGER.error("Error executing command: %s", e)

    async def async_send_lxc_command(
        self, nodeName: str, containerId: int, command: str
    ) -> None:
        """Send a command to a container."""
        endpoint = self._client.nodes(nodeName).lxc(containerId)
        try:
            if command == COMMAND_START:
                await endpoint.start()
            elif command == COMMAND_STOP:
                await endpoint.stop()
            elif command == COMMAND_REBOOT:
                await endpoint.reboot()
            elif command == COMMAND_SHUTDOWN:
                await endpoint.shutdown()
            elif command == COMMAND_SUSPEND:
                await endpoint.suspend()
            elif command == COMMAND_RESUME:
                await endpoint.resume()
            else:
                _LOGGER.error("Unknown command %s", command)
        except ProxmoxAPIResponseError as e:
            _LOGGER.error("Error executing command: %s", e)
