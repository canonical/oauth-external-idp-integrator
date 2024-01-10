# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit test config."""

from typing import Dict, Generator

import pytest
from ops.testing import Harness

from charm import OAuthIdpIntegratorCharm


@pytest.fixture
def config() -> Dict:
    return {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
        "introspection_endpoint": "https://oauth2.googleapis.com/tokeninfo",
        "issuer_url": "https://accounts.google.com",
        "jwks_endpoint": "https://www.googleapis.com/oauth2/v3/certs",
        "scope": "openid profile email",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v1/userinfo",
    }


@pytest.fixture
def harness() -> Generator[Harness, None, None]:
    harness = Harness(OAuthIdpIntegratorCharm)
    harness.set_leader(True)
    harness.begin_with_initial_hooks()
    yield harness
    harness.cleanup()
