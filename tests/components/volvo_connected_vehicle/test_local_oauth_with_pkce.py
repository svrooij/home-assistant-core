"""Test the Local OAuth2 implementation with PKCE for Volvo Connected Vehicle."""

import pytest

from homeassistant.components.volvo_connected_vehicle.local_oauth_with_pkce import (
    LocalOAuthWithPkce,
)


@pytest.mark.parametrize("code_verifier_length", [40, 129])
def test_generate_code_verifier_invalid_length(code_verifier_length: int) -> None:
    """Test generate_code_verifier with an invalid length."""
    with pytest.raises(ValueError):
        LocalOAuthWithPkce.generate_code_verifier(code_verifier_length)


@pytest.mark.parametrize("code_verifier", ["", "yyy", "a" * 129])
def test_compute_code_challenge_invalid_code_verifier(code_verifier: str) -> None:
    """Test compute_code_challenge with an invalid code_verifier."""
    with pytest.raises(ValueError):
        LocalOAuthWithPkce.compute_code_challenge(code_verifier)
