"""Base entity for Denon AVR settings entities."""

from collections.abc import Awaitable, Callable
from typing import Any

from denonavr import DenonAVR
from denonavr.exceptions import DenonAvrError

from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_TYPE
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from . import DenonavrConfigEntry
from .const import CONF_MANUFACTURER, DOMAIN


class DenonavrEntity(Entity):
    """Entity of a receiver setting, optionally updated by a telnet event."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _telnet_event: str | None = None

    def __init__(
        self, receiver: DenonAVR, config_entry: DenonavrConfigEntry, key: str
    ) -> None:
        """Initialize the entity."""
        self._receiver = receiver
        unique_id = config_entry.unique_id or config_entry.entry_id
        self._attr_unique_id = f"{unique_id}-{key}"
        self._attr_device_info = DeviceInfo(
            configuration_url=f"http://{config_entry.data[CONF_HOST]}/",
            hw_version=config_entry.data[CONF_TYPE],
            identifiers={(DOMAIN, unique_id)},
            manufacturer=config_entry.data[CONF_MANUFACTURER],
            model=config_entry.data[CONF_MODEL],
            name=receiver.name,
        )

    def _telnet_callback(self, zone: str, event: str, parameter: str) -> None:
        """Write the new state after the library processed the event."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register for telnet events."""
        if self._telnet_event:
            self._receiver.register_callback(self._telnet_event, self._telnet_callback)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister from telnet events."""
        if self._telnet_event:
            self._receiver.unregister_callback(
                self._telnet_event, self._telnet_callback
            )

    async def _async_command(
        self, command: Callable[..., Awaitable[Any]], *args: Any
    ) -> None:
        """Run a receiver command and translate library errors."""
        try:
            await command(*args)
        except DenonAvrError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="command_failed"
            ) from err
