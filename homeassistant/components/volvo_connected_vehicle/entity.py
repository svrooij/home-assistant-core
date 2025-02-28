"""Base entity for Volvo Connected Vehicle integration."""

from homeassistant.components.sensor import Entity

from .const import DOMAIN
from .coordinator import VolvoCoordinator


class VolvoEntity(Entity):
    """Base class for Volvo entities."""

    def __init__(
        self, coordinator: VolvoCoordinator, vin: str, name: str, icon: str
    ) -> None:
        """Initialize the entity."""
        self.coordinator = coordinator
        self._name = name
        self._icon = icon
        self.vin = vin
        self._attr_has_entity_name = True

        model = self.coordinator.data[vin].model
        self._attr_device_info = {
            "identifiers": {(DOMAIN, vin)},
            "name": f"Volvo {model}",
            "serial_number": vin,
            "model": model,
            "manufacturer": "Volvo",
        }

    @property
    def name(self):
        """Return the name of the entity."""
        return self._name

    @property
    def icon(self):
        """Return the icon of the entity."""
        return self._icon

    @property
    def available(self):
        """Return if entity is available."""
        return self.coordinator.last_update_success

    async def async_update(self):
        """Update the entity."""
        await self.coordinator.async_request_refresh()
