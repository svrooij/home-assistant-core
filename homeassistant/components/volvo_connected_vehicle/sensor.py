"""Support for Volvo sensors."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import VolvoCoordinator
from .entity import VolvoEntity


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Volvo sensors."""
    coordinator: VolvoCoordinator = config_entry.runtime_data

    entities = []

    for vin, data in coordinator.data.items():
        if data.battery_charge_level:
            entities.append(VolvoBatteryLevelEntity(coordinator, vin))
            entities.append(VolvoAvailableRangeEntity(coordinator, vin))
    async_add_entities(entities)


class VolvoBatteryLevelEntity(VolvoEntity, SensorEntity):
    """Representation of a Volvo Battery Level sensor."""

    def __init__(self, coordinator: VolvoCoordinator, vin: str) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, vin, "Battery Level", "mdi:car-battery")

    @property
    def native_value(self) -> float:
        """Return the state of the sensor."""
        return self.coordinator.data[self.vin].battery_charge_level.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.coordinator.data[self.vin].battery_charge_level.unit

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}_battery_level"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class of the sensor."""
        return SensorDeviceClass.BATTERY


class VolvoAvailableRangeEntity(VolvoEntity, SensorEntity):
    """Representation of a Volvo Available range sensor."""

    def __init__(self, coordinator: VolvoCoordinator, vin: str) -> None:
        """Initialize the sensor."""

        super().__init__(coordinator, vin, "Available range", "mdi:car-sports")

    @property
    def native_value(self) -> int:
        """Return the state of the sensor."""
        return self.coordinator.data[self.vin].distance_to_empty_battery.value

    @property
    def native_unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return self.coordinator.data[self.vin].distance_to_empty_battery.unit

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.vin}_expected_range"

    @property
    def device_class(self) -> SensorDeviceClass:
        """Return the device class of the sensor."""
        return SensorDeviceClass.DISTANCE
