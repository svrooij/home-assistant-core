"""Test the Volvo Connected Vehicle config flow."""

from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components.volvo_connected_vehicle.application_credentials import (
    SCOPES,
)
from homeassistant.components.volvo_connected_vehicle.config_flow import (
    _hash_string_urlsafe,
)
from homeassistant.components.volvo_connected_vehicle.const import (
    DOMAIN,
    OAUTH2_AUTHORIZE,
    OAUTH2_TOKEN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .const import ACCESS_TOKEN, CLIENT_ID, FAKE_SUB, ID_TOKEN

from tests.common import MockConfigEntry

REDIRECT_URI = "https://example.com/auth/external/callback"


async def test_full_flow(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock,
    current_request_with_host,
    setup_credentials,
) -> None:
    """Check full flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    state = config_entry_oauth2_flow._encode_jwt(  # noqa: SLF001
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT_URI,
        },
    )

    # Assert all the required parts of the url.
    # the code_challenge is a sha256 hash of the code_verifier which is generated randomly

    assert result["url"].startswith(f"{OAUTH2_AUTHORIZE}?")
    assert f"client_id={CLIENT_ID}" in result["url"]
    assert f"redirect_uri={REDIRECT_URI}" in result["url"]
    assert f"state={state}" in result["url"]
    assert f"scope={'+'.join(SCOPES)}" in result["url"]
    assert "response_type=code" in result["url"]
    assert "code_challenge=" in result["url"]
    assert "code_challenge_method=S256" in result["url"]

    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 200

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": ACCESS_TOKEN,
            "id_token": ID_TOKEN,
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    with patch(
        "homeassistant.components.volvo_connected_vehicle.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        await hass.config_entries.flow.async_configure(result["flow_id"])

    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
    assert len(mock_setup.mock_calls) == 1


async def test_flow_already_configured(
    hass: HomeAssistant,
    hass_client_no_auth,
    aioclient_mock,
) -> None:
    """Test we handle a flow that has already been configured."""
    assert len(hass.config_entries.async_entries(DOMAIN)) == 0
    first_entry = MockConfigEntry(
        domain=DOMAIN, unique_id=_hash_string_urlsafe(FAKE_SUB)
    )
    first_entry.add_to_hass(hass)
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    state = config_entry_oauth2_flow._encode_jwt(  # noqa: SLF001
        hass,
        {
            "flow_id": result["flow_id"],
            "redirect_uri": REDIRECT_URI,
        },
    )

    aioclient_mock.post(
        OAUTH2_TOKEN,
        json={
            "refresh_token": "mock-refresh-token",
            "access_token": ACCESS_TOKEN,
            "id_token": ID_TOKEN,
            "type": "Bearer",
            "expires_in": 60,
        },
    )

    client = await hass_client_no_auth()
    resp = await client.get(f"/auth/external/callback?code=abcd&state={state}")
    assert resp.status == 500
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1
