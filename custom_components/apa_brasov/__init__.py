"""Integrare APA Brasov pentru Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ApaBrasovAPI
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.NUMBER]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurare integrare APA Brasov."""
    api = ApaBrasovAPI(
        username=entry.data["username"],
        password=entry.data["password"],
    )

    coordinator = ApaBrasovCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "api": api,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Dezactivare integrare."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class ApaBrasovCoordinator(DataUpdateCoordinator):
    """Coordinator pentru actualizarea datelor APA Brasov."""

    def __init__(self, hass: HomeAssistant, api: ApaBrasovAPI) -> None:
        """Initializare coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(hours=SCAN_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self):
        """Fetch date de la API."""
        try:
            async with async_timeout.timeout(30):
                return await self.hass.async_add_executor_job(self.api.fetch_all_data)
        except Exception as err:
            raise UpdateFailed(f"Eroare la actualizarea datelor: {err}") from err
