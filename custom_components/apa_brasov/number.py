"""Entitate Number pentru introducerea indexului apometru - APA Brasov."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configureaza entitatea de introducere index."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api = hass.data[DOMAIN][entry.entry_id]["api"]
    async_add_entities([ApaBrasovIndexInput(coordinator, api, entry)])


class ApaBrasovIndexInput(CoordinatorEntity, NumberEntity):
    """Entitate pentru trimiterea autocitiri indexului apometru."""

    _attr_name = "Autocitire Index Apometru"
    _attr_icon = "mdi:water-pump"
    _attr_native_min_value = 0
    _attr_native_max_value = 999999
    _attr_native_step = 0.001
    _attr_native_unit_of_measurement = "m³"
    _attr_mode = NumberMode.BOX

    def __init__(self, coordinator, api, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._api = api
        self._attr_unique_id = f"{entry.entry_id}_autocitire_index"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="APA Brasov",
            manufacturer="Stefan Dram (dramuletz)",
            model="Compania Apa Brasov Integration",
            configuration_url="https://myaccount.apabrasov.ro",
        )
        # Valoarea curenta - folosim indexul din date
        self._current_value: float = 0.0

    @property
    def native_value(self) -> float:
        """Valoarea curenta (indexul din portal sau ce a fost setat)."""
        if self.coordinator.data:
            idx = self.coordinator.data.get("index_curent")
            if idx is not None:
                return float(idx)
        return self._current_value

    async def async_set_native_value(self, value: float) -> None:
        """Trimite autocitirea catre portal."""
        _LOGGER.info("Trimitere autocitire index: %.3f m³", value)
        try:
            success = await self.hass.async_add_executor_job(
                self._api.submit_autocitire, value
            )
            if success:
                self._current_value = value
                _LOGGER.info("Autocitire trimisa cu succes: %.3f m³", value)
                # Actualizeaza datele
                await self.coordinator.async_request_refresh()
            else:
                _LOGGER.warning(
                    "Autocitirea nu a putut fi confirmata de portal pentru valoarea %.3f", value
                )
        except Exception as err:
            _LOGGER.error("Eroare la trimiterea autocitiri: %s", err)
            raise
