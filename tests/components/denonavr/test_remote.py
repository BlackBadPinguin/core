"""The tests for the denonavr remote platform."""

from unittest.mock import MagicMock

from denonavr.exceptions import AvrCommandError
import pytest

from homeassistant.components.denonavr.const import CONF_USE_TELNET
from homeassistant.components.remote import (
    ATTR_COMMAND,
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    DOMAIN as REMOTE_DOMAIN,
    SERVICE_SEND_COMMAND,
    SERVICE_TURN_OFF,
    SERVICE_TURN_ON,
)
from homeassistant.const import ATTR_ENTITY_ID, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .test_media_player import setup_denonavr

ENTITY_ID = "remote.test_receiver"


async def test_send_command(hass: HomeAssistant, client: MagicMock) -> None:
    """Test commands are sent in order and repeated."""
    await setup_denonavr(hass)

    await hass.services.async_call(
        REMOTE_DOMAIN,
        SERVICE_SEND_COMMAND,
        {
            ATTR_ENTITY_ID: ENTITY_ID,
            ATTR_COMMAND: ["down", "enter"],
            ATTR_NUM_REPEATS: 2,
            ATTR_DELAY_SECS: 0,
        },
        blocking=True,
    )

    assert client.async_cursor_down.await_count == 2
    assert client.async_cursor_enter.await_count == 2


async def test_send_invalid_command(hass: HomeAssistant, client: MagicMock) -> None:
    """Test nothing is sent if one command is unknown."""
    await setup_denonavr(hass)

    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["up", "nope"]},
            blocking=True,
        )

    client.async_cursor_up.assert_not_awaited()


async def test_send_command_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test a library error is raised as a Home Assistant error."""
    client.async_back.side_effect = AvrCommandError("boom")
    await setup_denonavr(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            REMOTE_DOMAIN,
            SERVICE_SEND_COMMAND,
            {ATTR_ENTITY_ID: ENTITY_ID, ATTR_COMMAND: ["back"], ATTR_DELAY_SECS: 0},
            blocking=True,
        )


async def test_state_unknown_without_telnet(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the power state is unknown without Telnet."""
    await setup_denonavr(hass)

    assert hass.states.get(ENTITY_ID).state == STATE_UNKNOWN


async def test_state_follows_power_event(
    hass: HomeAssistant, client: MagicMock
) -> None:
    """Test the state follows power events with Telnet."""
    client.power = "STANDBY"
    await setup_denonavr(hass, options={CONF_USE_TELNET: True})

    assert hass.states.get(ENTITY_ID).state == STATE_OFF

    client.power = "ON"
    for call in client.register_callback.call_args_list:
        if call.args[0] == "ZM":
            call.args[1]("Main", "ZM", "ON")
    await hass.async_block_till_done()

    assert hass.states.get(ENTITY_ID).state == STATE_ON


@pytest.mark.parametrize(
    ("service", "method"),
    [
        (SERVICE_TURN_ON, "async_power_on"),
        (SERVICE_TURN_OFF, "async_power_off"),
    ],
)
async def test_power_services(
    hass: HomeAssistant, client: MagicMock, service: str, method: str
) -> None:
    """Test turning the remote on and off controls the receiver power."""
    await setup_denonavr(hass)

    await hass.services.async_call(
        REMOTE_DOMAIN, service, {ATTR_ENTITY_ID: ENTITY_ID}, blocking=True
    )

    getattr(client, method).assert_awaited_once_with()
