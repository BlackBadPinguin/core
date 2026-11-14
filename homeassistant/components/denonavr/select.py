"""Select entities for Denon AVR receiver settings."""

from dataclasses import dataclass
from typing import override

from denonavr import DenonAVR
from denonavr.const import MAIN_ZONE

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import DenonavrConfigEntry
from .const import CONF_USE_TELNET, DEFAULT_USE_TELNET
from .entity import DenonavrEntity

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class DenonavrSelectEntityDescription(SelectEntityDescription):
    """Describes a Denon AVR select entity."""

    telnet_event: str
    getter: str
    setter: str
    values: tuple[str, ...]


SELECTS: tuple[DenonavrSelectEntityDescription, ...] = (
    DenonavrSelectEntityDescription(
        key="dimmer",
        translation_key="dimmer",
        telnet_event="DIM",
        getter="dimmer",
        setter="async_dimmer",
        values=("Off", "Dark", "Dim", "Bright"),
    ),
    DenonavrSelectEntityDescription(
        key="eco_mode",
        translation_key="eco_mode",
        telnet_event="ECO",
        getter="eco_mode",
        setter="async_eco_mode",
        values=("Off", "On", "Auto"),
    ),
    DenonavrSelectEntityDescription(
        key="auto_standby",
        translation_key="auto_standby",
        telnet_event="STBY",
        getter="auto_standby",
        setter="async_auto_standby",
        values=("OFF", "15M", "30M", "60M", "2H", "4H", "8H"),
    ),
    DenonavrSelectEntityDescription(
        key="audio_restorer",
        translation_key="audio_restorer",
        telnet_event="PS",
        getter="audio_restorer",
        setter="async_audio_restorer",
        values=("Off", "Low", "Medium", "High"),
    ),
    DenonavrSelectEntityDescription(
        key="room_size",
        translation_key="room_size",
        telnet_event="PS",
        getter="room_size",
        setter="async_room_size",
        values=("S", "MS", "M", "ML", "L"),
        entity_registry_enabled_default=False,
    ),
    DenonavrSelectEntityDescription(
        key="video_processing_mode",
        translation_key="video_processing_mode",
        telnet_event="VS",
        getter="video_processing_mode",
        setter="async_video_processing_mode",
        values=("Auto", "Game", "Movie", "Bypass"),
        entity_registry_enabled_default=False,
    ),
    DenonavrSelectEntityDescription(
        key="hdmi_output",
        translation_key="hdmi_output",
        telnet_event="VS",
        getter="hdmi_output",
        setter="async_hdmi_output",
        values=("Auto", "HDMI1", "HDMI2"),
        entity_registry_enabled_default=False,
    ),
    DenonavrSelectEntityDescription(
        key="hdmi_audio_decode",
        translation_key="hdmi_audio_decode",
        telnet_event="VS",
        getter="hdmi_audio_decode",
        setter="async_hdmi_audio_decode",
        values=("AMP", "TV"),
        entity_registry_enabled_default=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: DenonavrConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Denon AVR select entities.

    These values are only pushed by Telnet, so they need it enabled.
    """
    if not config_entry.options.get(CONF_USE_TELNET, DEFAULT_USE_TELNET):
        return
    receiver = config_entry.runtime_data
    main = receiver.zones[MAIN_ZONE]
    async_add_entities(
        DenonavrSelect(main, config_entry, description) for description in SELECTS
    )


class DenonavrSelect(DenonavrEntity, SelectEntity):
    """Select for a receiver setting that has a fixed list of values."""

    _attr_entity_category = EntityCategory.CONFIG
    entity_description: DenonavrSelectEntityDescription

    def __init__(
        self,
        receiver: DenonAVR,
        config_entry: DenonavrConfigEntry,
        description: DenonavrSelectEntityDescription,
    ) -> None:
        """Initialize the select."""
        super().__init__(receiver, config_entry, description.key)
        self.entity_description = description
        self._telnet_event = description.telnet_event
        self._values = {value.lower(): value for value in description.values}
        self._attr_options = list(self._values)

    @property
    @override
    def current_option(self) -> str | None:
        """Return the selected option."""
        value = getattr(self._receiver, self.entity_description.getter)
        return value.lower() if value is not None else None

    @override
    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        await self._async_command(
            getattr(self._receiver, self.entity_description.setter),
            self._values[option],
        )
