"""The tests for the denonavr number platform."""

from unittest.mock import MagicMock

from denonavr.exceptions import AvrCommandError
import pytest

from homeassistant.components.denonavr.const import CONF_USE_TELNET
from homeassistant.components.number import (
    ATTR_VALUE,
    DOMAIN as NUMBER_DOMAIN,
    SERVICE_SET_VALUE,
)
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from .test_media_player import setup_denonavr

BASS_ENTITY_ID = "number.test_receiver_bass"
DELAY_ENTITY_ID = "number.test_receiver_audio_delay"
CHANNEL_ENTITY_ID = "number.test_receiver_front_left_level"


@pytest.fixture(autouse=True)
def receiver_values(client: MagicMock) -> None:
    """Provide receiver values for the number entities."""
    client.support_tone_control = True
    client.bass = 8
    client.treble = 6
    client.delay_time = 20
    client.vol = MagicMock()
    client.vol.channel_volumes = {"Front Left": 1.5}
    client.vol.channel_volume.return_value = 1.5


async def test_no_numbers_without_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the settings numbers are not created without Telnet."""
    await setup_denonavr(hass)

    assert hass.states.get(BASS_ENTITY_ID) is None


async def test_tone_is_centered_on_zero(hass: HomeAssistant, client: MagicMock) -> None:
    """Test the receiver tone range 0-12 is shown as -6 to +6 dB."""
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert float(hass.states.get(BASS_ENTITY_ID).state) == 2

    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: BASS_ENTITY_ID, ATTR_VALUE: -3},
        blocking=True,
    )

    client.async_set_bass.assert_awaited_once_with(3)


async def test_no_tone_without_support(hass: HomeAssistant, client: MagicMock) -> None:
    """Test bass and treble are not created if tone control is unsupported."""
    client.support_tone_control = False
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert hass.states.get(BASS_ENTITY_ID) is None


async def test_number_state_follows_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the number is updated from a Telnet event."""
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})
    client.bass = 10
    for call in client.register_callback.call_args_list:
        if call.args[0] == "PS":
            call.args[1]("Main", "PS", "BAS 54")
    await hass.async_block_till_done()

    assert float(hass.states.get(BASS_ENTITY_ID).state) == 4


async def test_delay_and_channel_numbers(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test delay and channel numbers are registered but disabled by default."""
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    entity_registry = er.async_get(hass)
    for entity_id in (DELAY_ENTITY_ID, CHANNEL_ENTITY_ID):
        assert hass.states.get(entity_id) is None
        entry = entity_registry.async_get(entity_id)
        assert entry is not None
        assert entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


async def test_number_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test a library error is raised as a Home Assistant error."""
    client.async_set_bass.side_effect = AvrCommandError("boom")
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: BASS_ENTITY_ID, ATTR_VALUE: 1},
            blocking=True,
        )
