"""Proxmox parent entity class."""

from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import ProxmoxDataUpdateCoordinator


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
    ) -> None:
        """Initialize the Proxmox entity."""
        super().__init__(coordinator)

        self.coordinator = coordinator
        self._attr_unique_id = unique_id
        self._attr_name = name
        self._host_name = host_name
        self._attr_icon = icon
        self._available = True
        self._node_name = node_name

        self._state = None

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self._available
