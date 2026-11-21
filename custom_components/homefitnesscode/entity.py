"""Shared entity metadata and update handling."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


class HFCEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, metric: str, name: str):
        super().__init__(coordinator)
        self.metric = metric
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.unique_id or coordinator.entry.entry_id}_{metric}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer="FTMS / HomeFitnessCode",
            model="Bluetooth fitness equipment",
        )

    @property
    def extra_state_attributes(self):
        return {
            "hfc_domain": DOMAIN,
            "hfc_key": self.coordinator.entry.entry_id,
            "hfc_metric": self.metric,
            "hfc_device_name": self.coordinator.entry.title,
        }
