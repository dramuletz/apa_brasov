"""Config flow pentru integrarea APA Brasov."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .api import ApaBrasovAPI, ApaBrasovAuthError, ApaBrasovAPIError
from .const import DOMAIN

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_credentials(hass: HomeAssistant, data: dict) -> dict:
    """Valideaza credentialele."""
    api = ApaBrasovAPI(username=data["username"], password=data["password"])
    await hass.async_add_executor_job(api.login)
    return {"title": f"APA Brasov - {data['username']}"}


class ApaBrasovConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow pentru APA Brasov."""

    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_credentials(self.hass, user_input)
            except ApaBrasovAuthError:
                errors["base"] = "invalid_auth"
            except ApaBrasovAPIError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={"portal_url": "https://myaccount.apabrasov.ro"},
        )
