"""Binary sensor to read Proxmox VE data."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import _LOGGER
from .coordinator import ProxmoxDataUpdateCoordinator
from .entity import ProxmoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entries: AddEntitiesCallback
) -> None:
    """Set up the Proxmox VE component."""
    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)
    # await entry.coordinator.async_config_entry_first_refresh()
    sensors = []
    coordinator: ProxmoxDataUpdateCoordinator = entry.coordinator
    for node_name, data in coordinator.data.nodes.items():
        _LOGGER.debug("node_name: %s data: %s", node_name, data)
        for vm_id in data.vms:
            sensors.append(
                ProxmoxVmSensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_vm_{vm_id}_cpu",
                    name="CPU usage",
                    icon="mdi:cpu-32-bit",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=True,
                    memory=False,
                )
            )
            sensors.append(
                ProxmoxVmSensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_vm_{vm_id}_memory",
                    name="Memory usage",
                    icon="mdi:memory",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=True,
                    memory=True,
                )
            )
        for container_id in data.containers:
            sensors.append(
                ProxmoxVmSensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_lxc_{container_id}_cpu",
                    name="CPU usage",
                    icon="mdi:cpu-32-bit",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=container_id,
                    qemu=False,
                    memory=False,
                )
            )
            sensors.append(
                ProxmoxVmSensor(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_lxc_{container_id}_memory",
                    name="Memory usage",
                    icon="mdi:memory",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=container_id,
                    qemu=False,
                    memory=True,
                )
            )

    async_add_entries(sensors)


class ProxmoxVmSensor(ProxmoxEntity, SensorEntity):
    """A sensor for reading Proxmox VE data.

    Args:
        coordinator (ProxmoxDataUpdateCoordinator): The coordinator.
        unique_id (str): The unique id.
        name (str): The name of the entity.
        icon (str): The icon of the entity.
        host_name (str): The host name.
        node_name (str): The node name.
        vm_id (int): The vm id.

    """

    # _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_suggested_display_precision = 1
    _attr_native_unit_of_measurement = "%"
    _attr_has_entity_name = True
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(
        self,
        coordinator: ProxmoxDataUpdateCoordinator,
        unique_id: str,
        name: str,
        icon: str,
        host_name: str,
        node_name: str,
        vm_id: int,
        qemu: bool,
        memory: bool,
    ) -> None:
        """Create the binary sensor for vms."""

        self._memory = memory
        super().__init__(
            coordinator, unique_id, name, icon, host_name, node_name, qemu, vm_id
        )

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""

        data = self.get_coordinator_data()
        if data is None:
            return None
        if self._memory:
            # calculate memory usage percentage
            if not data.memory or not data.memory_usage:
                return None
            return round(data.memory_usage / data.memory * 100, 3)
        # calculate cpu usage percentage cpu is a float and cpus is an int
        if not data.cpu or not data.cpus:
            return None
        return round(data.cpu / data.cpus * 100, 3)

    @property
    def available(self) -> bool:
        """Return sensor availability."""

        return True

    @property
    def entity_category(self) -> EntityCategory | None:
        """Return the entity category."""
        return EntityCategory.DIAGNOSTIC
