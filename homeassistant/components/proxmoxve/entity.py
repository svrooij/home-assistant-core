"""Proxmox parent entity class."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import (
    ProxmoxContainerData,
    ProxmoxDataUpdateCoordinator,
    ProxmoxVmData,
)


class ProxmoxEntity(CoordinatorEntity):
    """Represents any entity created for the Proxmox VE platform."""

    def __init__(
        self,
        coordinator: ProxmoxDataUpdateCoordinator,
        unique_id: str,
        name: str,
        icon: str,
        host_name: str,
        node_name: str,
        qemu: bool,
        vm_id: int,
    ) -> None:
        """Initialize the Proxmox entity."""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._host_name = host_name
        self._attr_icon = icon
        self._node_name = node_name
        self._qemu = qemu
        self._vm_id = vm_id

        self._state = None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.get_coordinator_data() is not None
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device information."""
        t = "lxc" if not self._qemu else "vm"
        data = self.get_coordinator_data()
        name = data.name if data else self._vm_id
        return DeviceInfo(
            # connections={(f"{self._host_name}", self._vm_id)},
            identifiers={
                (DOMAIN, f"{self._host_name}_{self._node_name}_{self._vm_id}"),
                # maybe add mac address?
            },
            manufacturer="Proxmox",
            name=f"{self._node_name} {t} {name}",
            model="Virtual Environment",
            sw_version=self.coordinator.version,
        )

    def get_coordinator_data(self) -> ProxmoxContainerData | ProxmoxVmData | None:
        """Return the data for the entity."""
        if self._qemu:
            return self.coordinator.data.nodes[self._node_name].vms[self._vm_id]
        return self.coordinator.data.nodes[self._node_name].containers[self._vm_id]
