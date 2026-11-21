"""Shared entity metadata and update handling."""
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .entity_catalog import inferred_machine


class HFCEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, metric: str, name: str):
        super().__init__(coordinator)
        self.metric = metric
        self._attr_name = name
        self._attr_unique_id = f"{coordinator.entry.unique_id or coordinator.entry.entry_id}_{metric}"
        kind = inferred_machine(dict(coordinator.entry.data), coordinator.entry.title)
        device_specs = {
            "headwind": ("Wahoo", "KICKR HEADWIND"),
            "rower": ("Top Sport / Christopeit", "WP5000"),
            "treadmill": ("HomeFitnessCode / FTMS", "Treadmill"),
            "bike": ("Tacx / FTMS", "Indoor cycle trainer"),
        }
        manufacturer, model = device_specs.get(kind, ("FTMS", "Bluetooth fitness equipment"))
        if kind == "bike" and "FLUX" in coordinator.entry.title.upper():
            manufacturer, model = "Tacx", "FLUX S Smart (T2900S)"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.unique_id or coordinator.entry.entry_id)},
            name=coordinator.entry.title,
            manufacturer=manufacturer,
            model=model,
        )

    @property
    def extra_state_attributes(self):
        return {
            "hfc_domain": DOMAIN,
            "hfc_key": self.coordinator.entry.entry_id,
            "hfc_metric": self.metric,
            "hfc_device_name": self.coordinator.entry.title,
        }
