"""The tests for the denonavr select platform."""

from unittest.mock import MagicMock

from denonavr.exceptions import AvrCommandError
import pytest

from homeassistant.components.denonavr.const import CONF_USE_TELNET
from homeassistant.components.select import (
    ATTR_OPTION,
    DOMAIN as SELECT_DOMAIN,
    SERVICE_SELECT_OPTION,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .test_media_player import setup_denonavr

DIMMER_ENTITY_ID = "select.test_receiver_display_brightness"


async def test_no_selects_without_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the settings selects are not created without Telnet."""
    await setup_denonavr(hass)

    assert hass.states.get(DIMMER_ENTITY_ID) is None


async def test_select_state_follows_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the select is updated from a Telnet event."""
    client.dimmer = None
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert hass.states.get(DIMMER_ENTITY_ID).state == STATE_UNKNOWN

    client.dimmer = "Bright"
    callbacks = [
        call.args[1]
        for call in client.register_callback.call_args_list
        if call.args[0] == "DIM"
    ]
    for callback in callbacks:
        callback("Main", "DIM", " BRI")
    await hass.async_block_till_done()

    assert hass.states.get(DIMMER_ENTITY_ID).state == "bright"


async def test_select_option(hass: HomeAssistant, client: MagicMock) -> None:
    """Test selecting an option sends the library value."""
    client.dimmer = "Off"
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: DIMMER_ENTITY_ID, ATTR_OPTION: "dark"},
        blocking=True,
    )

    client.async_dimmer.assert_awaited_once_with("Dark")


async def test_select_option_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test a library error is raised as a Home Assistant error."""
    client.dimmer = "Off"
    client.async_dimmer.side_effect = AvrCommandError("boom")
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: DIMMER_ENTITY_ID, ATTR_OPTION: "dark"},
            blocking=True,
        )
