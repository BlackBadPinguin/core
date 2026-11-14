"""The tests for the denonavr switch platform."""

from unittest.mock import MagicMock

from denonavr.exceptions import AvrCommandError
import pytest

from homeassistant.components.denonavr.const import CONF_USE_TELNET
from homeassistant.components.switch import (
    DOMAIN as SWITCH_DOMAIN,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .test_media_player import setup_denonavr

GRAPHIC_EQ_ENTITY_ID = "switch.test_receiver_graphic_equalizer"


async def test_no_switches_without_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the settings switches are not created without Telnet."""
    await setup_denonavr(hass)

    assert hass.states.get(GRAPHIC_EQ_ENTITY_ID) is None


async def test_switch_state_follows_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the switch is updated from a Telnet event."""
    client.graphic_eq = None
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert hass.states.get(GRAPHIC_EQ_ENTITY_ID).state == STATE_UNKNOWN

    client.graphic_eq = True
    for call in client.register_callback.call_args_list:
        if call.args[0] == "PS":
            call.args[1]("Main", "PS", "GEQ ON")
    await hass.async_block_till_done()

    assert hass.states.get(GRAPHIC_EQ_ENTITY_ID).state == STATE_ON


@pytest.mark.parametrize(
    ("service", "method"),
    [
        (SERVICE_TURN_ON, "async_graphic_eq_on"),
        (SERVICE_TURN_OFF, "async_graphic_eq_off"),
    ],
)
async def test_switch_service(
    hass: HomeAssistant, client: MagicMock, service: str, method: str
) -> None:
    """Test turning the switch on and off calls the library."""
    client.graphic_eq = False
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert hass.states.get(GRAPHIC_EQ_ENTITY_ID).state == STATE_OFF

    await hass.services.async_call(
        SWITCH_DOMAIN,
        service,
        {ATTR_ENTITY_ID: GRAPHIC_EQ_ENTITY_ID},
        blocking=True,
    )

    getattr(client, method).assert_awaited_once_with()


async def test_switch_service_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test a library error is raised as a Home Assistant error."""
    client.graphic_eq = False
    client.async_graphic_eq_on.side_effect = AvrCommandError("boom")
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {ATTR_ENTITY_ID: GRAPHIC_EQ_ENTITY_ID},
            blocking=True,
        )
