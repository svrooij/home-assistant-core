"""Binary sensor to read Proxmox VE data."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import _LOGGER, COMMAND_NONE, COMMANDS_CONTAINER, COMMANDS_VM
from .coordinator import ProxmoxDataUpdateCoordinator
from .entity import ProxmoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entries: AddEntitiesCallback
) -> None:
    """Set up the Proxmox VE component."""
    _LOGGER.debug("setup %s with config:%s", entry.title, entry.data)
    # await entry.coordinator.async_config_entry_first_refresh()
    select_entities = []
    coordinator: ProxmoxDataUpdateCoordinator = entry.coordinator
    for node_name, data in coordinator.data.nodes.items():
        _LOGGER.debug("node_name: %s data: %s", node_name, data)

        select_entities.extend(
            [
                ProxmoxSelectEntity(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_vm_{vm_id}_action",
                    name="Action",
                    icon="mdi:play",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=True,
                )
                for vm_id in data.vms
            ]
        )

        select_entities.extend(
            [
                ProxmoxSelectEntity(
                    coordinator=coordinator,
                    unique_id=f"proxmox_{node_name}_lxc_{vm_id}_action",
                    name="Action",
                    icon="mdi:play",
                    host_name=entry.title,
                    node_name=node_name,
                    vm_id=vm_id,
                    qemu=False,
                )
                for vm_id in data.containers
            ]
        )

    async_add_entries(select_entities)


class ProxmoxSelectEntity(ProxmoxEntity, SelectEntity):
    """A binary sensor for reading Proxmox VE data.

    Args:
        coordinator (ProxmoxDataUpdateCoordinator): The coordinator.
        unique_id (str): The unique id.
        name (str): The name of the entity.
        icon (str): The icon of the entity.
        host_name (str): The host name.
        node_name (str): The node name.
        vm_id (int): The vm id.
        qemu (bool): True if the vm is a qemu vm.

    """

    # _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_has_entity_name = True

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
    ) -> None:
        """Create the binary sensor for vms."""

        self._node_name = node_name
        self._vm_id = vm_id
        self._qemu = qemu
        super().__init__(
            coordinator, unique_id, name, icon, host_name, node_name, qemu, vm_id
        )

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""

        _LOGGER.debug("Select option %s", option)
        # Do something with the option (like sending it to proxmox)
        if not self._qemu and option in COMMANDS_CONTAINER:
            await self.coordinator.async_send_lxc_command(
                self._node_name, self._vm_id, option
            )
        elif self._qemu and option in COMMANDS_VM:
            await self.coordinator.async_send_qemu_command(
                self._node_name, self._vm_id, option
            )
        # Note sure how to reset back to COMMAND_NONE after sending the command
        self._attr_current_option = COMMAND_NONE

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""

        return COMMAND_NONE

    @property
    def options(self) -> list[str]:
        """Return a set of selectable options."""
        if not self._qemu:
            return [COMMAND_NONE, *COMMANDS_CONTAINER]
        return [COMMAND_NONE, *COMMANDS_VM]

    @property
    def entity_category(self) -> EntityCategory:
        """Return the entity category."""
        return EntityCategory.DIAGNOSTIC
