"""Senzori pentru integrarea APA Brasov."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


@dataclass(frozen=True)
class ApaBrasovSensorDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] = field(default=lambda d: None)
    attr_fn: Callable[[dict], dict] = field(default=lambda d: {})


SENZORI: tuple[ApaBrasovSensorDescription, ...] = (

    # ── Sold ───────────────────────────────────────────────────────
    ApaBrasovSensorDescription(
        key="sold",
        name="Total de Plată",
        icon="mdi:cash",
        native_unit_of_measurement="RON",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.get("sold"),
    ),

    # ── Index apometru ─────────────────────────────────────────────
    ApaBrasovSensorDescription(
        key="index_curent",
        name="Index Apometru Curent",
        icon="mdi:counter",
        native_unit_of_measurement="m³",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.get("index_curent"),
        attr_fn=lambda d: {
            "data_citire": d.get("data_citire_curenta"),
            "index_anterior": d.get("index_anterior"),
            "data_citire_anterioara": d.get("data_citire_anterioara"),
            "cod_autocitire": d.get("cod_autocitire"),
        },
    ),
    ApaBrasovSensorDescription(
        key="consum_mc",
        name="Consum Ultima Perioadă",
        icon="mdi:water",
        native_unit_of_measurement="m³",
        device_class=SensorDeviceClass.WATER,
        state_class=SensorStateClass.TOTAL,
        value_fn=lambda d: d.get("consum_mc"),
    ),

    # ── Arhiva plati (ca atribute JSON pentru grafic) ──────────────
    ApaBrasovSensorDescription(
        key="arhiva_plati",
        name="Arhivă Plăți",
        icon="mdi:chart-line",
        native_unit_of_measurement="RON",
        state_class=SensorStateClass.TOTAL,
        # state = suma totala platita
        value_fn=lambda d: d.get("total_plati"),
        attr_fn=lambda d: {
            "plati": d.get("arhiva_plati", []),
            "note": "Lista platilor. Format: [{'data': '08.02.2024', 'suma': 165.0, 'serie': 'OP 1', 'note': 'Ordin de plata'}, ...]",
        },
    ),

    # ── Ultima factura ─────────────────────────────────────────────
    ApaBrasovSensorDescription(
        key="ultima_factura",
        name="Ultima Factură",
        icon="mdi:receipt-text",
        native_unit_of_measurement="RON",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d["facturi"][0]["suma"] if d.get("facturi") else None,
        attr_fn=lambda d: {
            "cod": d["facturi"][0].get("cod"),
            "serie_nr": d["facturi"][0].get("serie_nr"),
            "data_emitere": d["facturi"][0].get("data_emitere"),
            "data_scadenta": d["facturi"][0].get("data_scadenta"),
            "tva": d["facturi"][0].get("tva"),
        } if d.get("facturi") else {},
    ),

    # ── Date utilizator ────────────────────────────────────────────
    ApaBrasovSensorDescription(
        key="date_utilizator",
        name="Date Utilizator",
        icon="mdi:account-details",
        value_fn=lambda d: d.get("cod_client"),
        attr_fn=lambda d: {
            "cod_client": d.get("cod_client"),
            "nr_contract": d.get("nr_contract"),
            "data_contract": d.get("data_contract"),
            "valabilitate": d.get("valabilitate"),
            "tip_serviciu": d.get("tip_serviciu"),
            "in_reziliere": d.get("in_reziliere"),
            "adresa": d.get("adresa"),
            "cod_autocitire": d.get("cod_autocitire"),
            "adresa_consum": d.get("adresa_consum"),
            "contract_nr": d.get("contract_nr"),
        },
    ),

    # ── Ultima actualizare ─────────────────────────────────────────
    ApaBrasovSensorDescription(
        key="last_update",
        name="Ultima Actualizare",
        icon="mdi:clock-check-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda d: d.get("last_update"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    async_add_entities(
        ApaBrasovSensor(coordinator, description, entry)
        for description in SENZORI
    )


class ApaBrasovSensor(CoordinatorEntity, SensorEntity):
    entity_description: ApaBrasovSensorDescription

    def __init__(self, coordinator, description: ApaBrasovSensorDescription, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="APA Brasov",
            manufacturer="Stefan Dram (dramuletz)",
            model="Compania Apa Brasov Integration",
            configuration_url="https://myaccount.apabrasov.ro",
        )

    @property
    def native_value(self) -> Any:
        if self.coordinator.data:
            try:
                return self.entity_description.value_fn(self.coordinator.data)
            except Exception:
                return None
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        if self.coordinator.data:
            try:
                return self.entity_description.attr_fn(self.coordinator.data)
            except Exception:
                return {}
        return {}
