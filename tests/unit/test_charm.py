# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


from typing import Dict

from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


def test_config(
    harness: Harness, config: Dict
) -> None:

    # charm not configured, should have the blocked status
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert 'Missing required configuration' in harness.charm.unit.status.message

    incomplete_config = {
        "scope": "openid profile email",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v1/userinfo"
    }
    harness.update_config(incomplete_config)

    # still blocked because required fields are missing
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert 'Missing required configuration' in harness.charm.unit.status.message

    harness.update_config(config)
    # now config is okay, but the client relation is missing, so still blocked
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert 'Missing client relation' in harness.charm.unit.status.message


def test_oauth_relation(
    harness: Harness, config: Dict
) -> None:

    harness.update_config(config)
    relation_id = harness.add_relation("oauth", "kafka")

    # config is fine and the client is related
    assert isinstance(harness.charm.unit.status, ActiveStatus)

    app_data = harness.get_relation_data(relation_id, harness.charm.app)
    assert app_data == config

    harness.remove_relation(relation_id)
    assert isinstance(harness.charm.unit.status, BlockedStatus)

