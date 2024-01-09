#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
from pathlib import Path
from typing import Dict

import pytest
import yaml
from pytest_operator.plugin import OpsTest

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
APP_NAME = METADATA["name"]


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


@pytest.mark.abort_on_fail
async def test_build_and_deploy(ops_test: OpsTest, config: Dict) -> None:
    """Build the charm-under-test and deploy it together with related charms.

    Assert on the unit status before any relations/configurations take place.
    """
    # build and deploy charm from local source folder
    charm = await ops_test.build_charm(".")
    await ops_test.model.deploy(charm, application_name=APP_NAME, config=config, series="jammy")

    # issuing dummy update_status just to trigger an event
    async with ops_test.fast_forward():
        await ops_test.model.wait_for_idle(
            apps=[APP_NAME],
            timeout=1000,
        )
        assert ops_test.model.applications[APP_NAME].units[0].workload_status == "blocked"
