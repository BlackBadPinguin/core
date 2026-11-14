"""Remote entity for Denon AVR on-screen menu navigation."""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Any, override

from denonavr import DenonAVR
from denonavr.const import MAIN_ZONE, POWER_ON

from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DEFAULT_DELAY_SECS,
    DEFAULT_NUM_REPEATS,
    RemoteEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DenonavrConfigEntry
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET, DOMAIN
from .entity import DenonavrEntity

PARALLEL_UPDATES = 1

POWER_EVENTS = ("ZM", "PW")

COMMANDS: dict[str, Callable[[DenonAVR], Awaitable[None]]] = {
    "up": lambda r: r.async_cursor_up(),
    "down": lambda r: r.async_cursor_down(),
    "left": lambda r: r.async_cursor_left(),
    "right": lambda r: r.async_cursor_right(),
    "enter": lambda r: r.async_cursor_enter(),
    "back": lambda r: r.async_back(),
    "info": lambda r: r.async_info(),
    "options": lambda r: r.async_options(),
    "menu": lambda r: r.async_settings_menu(),
    "page_up": lambda r: r.async_page_up(),
    "page_down": lambda r: r.async_page_down(),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Denon AVR remote."""
    main = config_entry.runtime_data.zones[MAIN_ZONE]
    async_add_entities([DenonavrRemote(main, config_entry)])


class DenonavrRemote(DenonavrEntity, RemoteEntity):
    """Remote for the on-screen menu of a Denon AVR receiver."""

    _attr_name = None

    def __init__(self, receiver: DenonAVR, config_entry: DenonavrConfigEntry) -> None:
        """Initialize the remote."""
        super().__init__(receiver, config_entry, "remote")
        self._use_telnet = config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET)

    @override
    async def async_added_to_hass(self) -> None:
        """Register for power events."""
        if self._use_telnet:
            for event in POWER_EVENTS:
                self._receiver.register_callback(event, self._telnet_callback)

    @override
    async def async_will_remove_from_hass(self) -> None:
        """Unregister from power events."""
        if self._use_telnet:
            for event in POWER_EVENTS:
                self._receiver.unregister_callback(event, self._telnet_callback)

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the receiver is on.

        The power state is only kept current by Telnet.
        """
        if not self._use_telnet:
            return None
        return self._receiver.power == POWER_ON

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the receiver on."""
        await self._async_command(self._receiver.async_power_on)

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the receiver off."""
        await self._async_command(self._receiver.async_power_off)

    @override
    async def async_send_command(self, command: Iterable[str], **kwargs: Any) -> None:
        """Send navigation commands to the receiver."""
        commands = list(command)
        for single_command in commands:
            if single_command not in COMMANDS:
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="invalid_remote_command",
                    translation_placeholders={
                        "command": single_command,
                        "commands": ", ".join(COMMANDS),
                    },
                )

        num_repeats = kwargs.get(ATTR_NUM_REPEATS, DEFAULT_NUM_REPEATS)
        delay_secs = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)
        for _ in range(num_repeats):
            for single_command in commands:
                await self._async_command(COMMANDS[single_command], self._receiver)
                await asyncio.sleep(delay_secs)
