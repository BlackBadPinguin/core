"""Switch entities for Denon AVR receiver settings."""

from dataclasses import dataclass
from typing import Any, override

from denonavr import DenonAVR
from denonavr.const import MAIN_ZONE

from homeassistant.components.switch import SwitchEntity, SwitchEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DenonavrConfigEntry
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonavrEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DenonavrSwitchEntityDescription(SwitchEntityDescription):
    """Describes a Denon AVR switch entity."""

    telnet_event: str
    getter: str
    turn_on: str
    turn_off: str


SWITCHES: tuple[DenonavrSwitchEntityDescription, ...] = (
    DenonavrSwitchEntityDescription(
        key="graphic_eq",
        translation_key="graphic_eq",
        telnet_event="PS",
        getter="graphic_eq",
        turn_on="async_graphic_eq_on",
        turn_off="async_graphic_eq_off",
    ),
    DenonavrSwitchEntityDescription(
        key="headphone_eq",
        translation_key="headphone_eq",
        telnet_event="PS",
        getter="headphone_eq",
        turn_on="async_headphone_eq_on",
        turn_off="async_headphone_eq_off",
        entity_registry_enabled_default=False,
    ),
    DenonavrSwitchEntityDescription(
        key="bt_transmitter",
        translation_key="bt_transmitter",
        telnet_event="BT",
        getter="bt_transmitter",
        turn_on="async_bt_transmitter_on",
        turn_off="async_bt_transmitter_off",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Denon AVR switch entities.

    These values are only pushed by Telnet, so they need it enabled.
    """
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    main = config_entry.runtime_data.zones[MAIN_ZONE]
    async_add_entities(
        DenonavrSwitch(main, config_entry, description) for description in SWITCHES
    )


class DenonavrSwitch(DenonavrEntity, SwitchEntity):
    """Switch for an on/off receiver setting."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: DenonavrSwitchEntityDescription

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        description: DenonavrSwitchEntityDescription,
    ) -> None:
        """Initialize the switch."""
        super().__init__(receiver, config_entry, description.key)
        self.entity_description = description
        self._telnet_event = description.telnet_event

    @property
    @override
    def is_on(self) -> bool | None:
        """Return true if the setting is on."""
        return getattr(self._receiver, self.entity_description.getter)

    @override
    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the setting on."""
        await self._async_command(
            getattr(self._receiver, self.entity_description.turn_on)
        )

    @override
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the setting off."""
        await self._async_command(
            getattr(self._receiver, self.entity_description.turn_off)
        )
