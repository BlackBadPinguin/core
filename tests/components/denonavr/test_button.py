"""The tests for the denonavr button platform."""

from unittest.mock import MagicMock

from denonavr.exceptions import AvrCommandError
import pytest

from homeassistant.components.button import DOMAIN as BUTTON_DOMAIN, SERVICE_PRESS
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .test_media_player import setup_denonavr

QUICK_SELECT_ENTITY_ID = "button.test_receiver_quick_select_2"


async def test_quick_select_press(hass: HomeAssistant, client: MagicMock) -> None:
    """Test pressing a quick select button recalls that quick select."""
    await setup_denonavr(hass)

    await hass.services.async_call(
        BUTTON_DOMAIN,
        SERVICE_PRESS,
        {"entity_id": QUICK_SELECT_ENTITY_ID},
        blocking=True,
    )

    client.async_quick_select_mode.assert_awaited_once_with(2)


async def test_button_error(hass: HomeAssistant, client: MagicMock) -> None:
    """Test a library error is raised as a Home Assistant error."""
    client.async_quick_select_mode.side_effect = AvrCommandError("boom")
    await setup_denonavr(hass)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            BUTTON_DOMAIN,
            SERVICE_PRESS,
            {"entity_id": QUICK_SELECT_ENTITY_ID},
            blocking=True,
        )
