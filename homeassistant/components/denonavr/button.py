"""Button entities for Denon AVR receiver commands."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import override

from denonavr import DenonAVR
from denonavr.const import MAIN_ZONE

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DenonavrConfigEntry
from .entity import DenonavrEntity

PARALLEL_UPDATES = 1

# The library rejects quick select 5.
QUICK_SELECT_NUMBERS = (1, 2, 3, 4)


@dataclass(frozen=True, kw_only=True)
class DenonavrButtonEntityDescription(ButtonEntityDescription):
    """Describes a Denon AVR button entity."""

    press_fn: Callable[[DenonAVR], Awaitable[None]]


BUTTONS: tuple[DenonavrButtonEntityDescription, ...] = tuple(
    DenonavrButtonEntityDescription(
        key=f"quick_select_{number}",
        translation_key="quick_select",
        translation_placeholders={"number": str(number)},
        press_fn=lambda r, number=number: r.async_quick_select_mode(number),
    )
    for number in QUICK_SELECT_NUMBERS
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Denon AVR button entities."""
    main = config_entry.runtime_data.zones[MAIN_ZONE]
    async_add_entities(
        DenonavrButton(main, config_entry, description) for description in BUTTONS
    )


class DenonavrButton(DenonavrEntity, ButtonEntity):
    """Button that sends a command to the receiver."""

    entity_description: DenonavrButtonEntityDescription

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        description: DenonavrButtonEntityDescription,
    ) -> None:
        """Initialize the button."""
        super().__init__(receiver, config_entry, description.key)
        self.entity_description = description

    @override
    async def async_press(self) -> None:
        """Send the command."""
        await self._async_command(self.entity_description.press_fn, self._receiver)
