"""Data update coordinator for the Proximity integration."""

from dataclasses import dataclass
from datetime import timedelta

from pyproxmox_ve import ProxmoxVEAPI
from pyproxmox_ve.exceptions import (
    ProxmoxAPIAuthenticationError,
    ProxmoxAPIJSONKeyError,
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
class ProxmoxData:
    """ProximityCoordinatorData class."""

    nodes: dict[str, ProxmoxNodeData]


DEFAULT_PROXMOX_DATA = ProxmoxData({})


class ProxmoxDataUpdateCoordinator(DataUpdateCoordinator[ProxmoxData]):
    """Proximity data update coordinator."""

    _entry_configuration: dict[str, any]
    _client: ProxmoxVEAPI | None
    _version: str | None

    def __init__(
        self, hass: HomeAssistant, friendly_name: str, config: dict[str, any]
    ) -> None:
        """Initialize the Proxmox coordinator."""
        self._entry_configuration = config

        super().__init__(
            hass,
            _LOGGER,
            name=friendly_name,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

        self.data = ProxmoxData(DEFAULT_PROXMOX_DATA)

        self.state_change_data: StateChangedData | None = None

    async def _async_setup(self):
        """Set up the Proxmox coordinator."""
        await self.configure_client()
        return await super()._async_setup()

    async def configure_client(self) -> None:
        """Configure the Proxmox client."""
        try:
            self._client = ProxmoxVEAPI(
                url=f"https://{self._entry_configuration[CONF_HOST]}:{self._entry_configuration.get(CONF_PORT, DEFAULT_PORT)}/",
                username=self._entry_configuration[CONF_USERNAME],
                realm=self._entry_configuration[CONF_REALM],
                api_token=self._entry_configuration[CONF_TOKEN],
                api_token_id=self._entry_configuration[CONF_TOKEN_ID],
                verify_ssl=self._entry_configuration[CONF_VERIFY_SSL],
            )
        except ProxmoxAPIAuthenticationError as e:
            _LOGGER.error("Error authenticating with Proxmox: %s", e)
            raise

    async def _async_update_data(self):
        # if self._client is None:
        #     await self.configure_client()
        new_data = ProxmoxData({})
        for node in self._entry_configuration[CONF_NODES]:
            k = node[CONF_NODE]
            try:
                new_data.nodes[k] = await self._async_get_node_data(k, node)
            except ProxmoxAPIJSONKeyError as e:
                _LOGGER.error("Error fetching node data: %s", e)
                continue
        return new_data

    async def _async_get_node_data(
        self, nodeName: str, node: dict[str, any]
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
        container = await self._client.query(
            "GET", f"/nodes/{nodeName}/lxc/{containerId}/status/current"
        )
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
        vm = await self._client.query(
            "GET", f"/nodes/{nodeName}/qemu/{vmId}/status/current"
        )
        return ProxmoxVmData(
            vm["cpu"],
            vm["cpus"],
            vm["maxmem"],
            vm["mem"],
            vm["name"],
            vm["status"] == "running",
            vm["agent"] == 1,
        )
