"""Number entities for Denon AVR receiver settings."""

from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass
from typing import override

from denonavr import DenonAVR
from denonavr.const import MAIN_ZONE

from homeassistant.components.number import (
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import EntityCategory, UnitOfSoundPressure, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DenonavrConfigEntry
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonavrEntity

PARALLEL_UPDATES = 1

# The receiver reports tone values from 0 to 12, with 6 being flat.
TONE_OFFSET = 6


@dataclass(frozen=True, kw_only=True)
class DenonavrNumberEntityDescription(NumberEntityDescription):
    """Describes a Denon AVR number entity."""

    telnet_event: str
    value_fn: Callable[[DenonAVR], float | None]
    set_fn: Callable[[DenonAVR, float], Awaitable[None]]


def _tone_value(value: int | None) -> int | None:
    return None if value is None else value - TONE_OFFSET


TONE_NUMBERS: tuple[DenonavrNumberEntityDescription, ...] = (
    DenonavrNumberEntityDescription(
        key="bass",
        translation_key="bass",
        telnet_event="PS",
        native_min_value=-TONE_OFFSET,
        native_max_value=TONE_OFFSET,
        native_step=1,
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        value_fn=lambda r: _tone_value(r.bass),
        set_fn=lambda r, v: r.async_set_bass(int(v) + TONE_OFFSET),
    ),
    DenonavrNumberEntityDescription(
        key="treble",
        translation_key="treble",
        telnet_event="PS",
        native_min_value=-TONE_OFFSET,
        native_max_value=TONE_OFFSET,
        native_step=1,
        native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
        value_fn=lambda r: _tone_value(r.treble),
        set_fn=lambda r, v: r.async_set_treble(int(v) + TONE_OFFSET),
    ),
)

DELAY_TIME_NUMBER = DenonavrNumberEntityDescription(
    key="delay_time",
    translation_key="delay_time",
    telnet_event="PS",
    native_min_value=0,
    native_max_value=999,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.MILLISECONDS,
    mode=NumberMode.BOX,
    entity_registry_enabled_default=False,
    value_fn=lambda r: r.delay_time,
    set_fn=lambda r, v: r.async_delay_time(int(v)),
)


def _channel_volume_numbers(
    receiver: DenonAVR,
) -> Iterator[DenonavrNumberEntityDescription]:
    for channel in receiver.vol.channel_volumes or {}:
        yield DenonavrNumberEntityDescription(
            key=f"channel_volume_{channel.lower().replace(' ', '_')}",
            translation_key="channel_volume",
            translation_placeholders={"channel": channel},
            telnet_event="CV",
            native_min_value=-12,
            native_max_value=12,
            native_step=0.5,
            native_unit_of_measurement=UnitOfSoundPressure.DECIBEL,
            entity_registry_enabled_default=False,
            value_fn=lambda r, channel=channel: r.vol.channel_volume(channel),
            set_fn=lambda r, v, channel=channel: r.vol.async_channel_volume(channel, v),
        )


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Denon AVR number entities.

    These values are only pushed by Telnet, so they need it enabled.
    """
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    main = config_entry.runtime_data.zones[MAIN_ZONE]
    descriptions = [DELAY_TIME_NUMBER, *_channel_volume_numbers(main)]
    if main.support_tone_control:
        descriptions.extend(TONE_NUMBERS)
    async_add_entities(
        DenonavrNumber(main, config_entry, description) for description in descriptions
    )


class DenonavrNumber(DenonavrEntity, NumberEntity):
    """Number for a receiver setting with a numeric range."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: DenonavrNumberEntityDescription

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        description: DenonavrNumberEntityDescription,
    ) -> None:
        """Initialize the number."""
        super().__init__(receiver, config_entry, description.key)
        self.entity_description = description
        self._telnet_event = description.telnet_event

    @property
    @override
    def native_value(self) -> float | None:
        """Return the current value."""
        return self.entity_description.value_fn(self._receiver)

    @override
    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        await self._async_command(self.entity_description.set_fn, self._receiver, value)
