# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""Charm unit tests."""

from typing import Dict

import pytest
from charms.hydra.v0.oauth import CLIENT_SECRET_FIELD
from ops.model import ActiveStatus, BlockedStatus
from ops.testing import Harness


def test_config(harness: Harness, config: Dict) -> None:
    # charm not configured, should have the blocked status
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert "Missing required configuration" in harness.charm.unit.status.message

    incomplete_config = {
        "scope": "openid profile email",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v1/userinfo",
    }
    harness.update_config(incomplete_config)

    # still blocked because required fields are missing
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert "Missing required configuration" in harness.charm.unit.status.message

    harness.update_config(config)
    # now config is okay, but the client relation is missing, so still blocked
    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert "Missing client relation" in harness.charm.unit.status.message


def test_oauth_relation(harness: Harness, config: Dict) -> None:
    harness.update_config(config)
    relation_id = harness.add_relation("oauth", "kafka")

    # config is fine and the client is related
    assert isinstance(harness.charm.unit.status, ActiveStatus)

    app_data = harness.get_relation_data(relation_id, harness.charm.app)
    assert app_data == {
        "authorization_endpoint": "https://accounts.google.com/o/oauth2/auth",
        "introspection_endpoint": "https://oauth2.googleapis.com/tokeninfo",
        "issuer_url": "https://accounts.google.com",
        "jwks_endpoint": "https://www.googleapis.com/oauth2/v3/certs",
        "scope": "openid profile email",
        "token_endpoint": "https://oauth2.googleapis.com/token",
        "userinfo_endpoint": "https://www.googleapis.com/oauth2/v1/userinfo",
        "jwt_access_token": "False",
    }


def _request_client(harness: Harness) -> int:
    relation_id = harness.add_relation("oauth", "oauth-client")
    harness.update_relation_data(
        relation_id,
        "oauth-client",
        {
            "redirect_uri": "https://example.com/oauth2/callback",
            "scope": "openid email",
            "audience": "[]",
            "grant_types": '["authorization_code"]',
            "token_endpoint_auth_method": "client_secret_basic",
        },
    )
    return relation_id


def _shared_secret(harness: Harness, relation_id: int) -> str:
    data = harness.get_relation_data(relation_id, harness.charm.app)
    return harness.model.get_secret(id=data["client_secret_id"]).peek_content()[
        CLIENT_SECRET_FIELD
    ]


def test_juju_secret_is_shared_without_plaintext_config_or_relation_data(
    harness: Harness, config: Dict
) -> None:
    secret_id = harness.add_user_secret({"client-secret": "vault-sourced-test-value"})
    harness.grant_secret(secret_id, harness.charm.app)
    harness.update_config({**config, "client-secret": secret_id, "client_id": "google-client"})

    relation_id = _request_client(harness)
    data = harness.get_relation_data(relation_id, harness.charm.app)

    assert data["client_id"] == "google-client"
    assert data["client_secret_id"]
    assert _shared_secret(harness, relation_id) == "vault-sourced-test-value"
    assert "vault-sourced-test-value" not in str(data)
    assert "vault-sourced-test-value" not in str(dict(harness.charm.config))
    assert isinstance(harness.charm.unit.status, ActiveStatus)


@pytest.mark.parametrize("content", [{"wrong-key": "test-value"}, {"client-secret": "   "}])
def test_invalid_secret_does_not_fall_back_to_plaintext(
    harness: Harness, config: Dict, content: Dict
) -> None:
    secret_id = harness.add_user_secret(content)
    harness.grant_secret(secret_id, harness.charm.app)
    harness.update_config({**config, "client-secret": secret_id, "client_secret": "legacy-value"})

    relation_id = _request_client(harness)

    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert "client-secret" in harness.charm.unit.status.message
    assert "client_secret_id" not in harness.get_relation_data(relation_id, harness.charm.app)


def test_missing_grant_blocks_then_recovers_on_update_status(
    harness: Harness, config: Dict
) -> None:
    secret_id = harness.add_user_secret({"client-secret": "granted-later"})
    harness.update_config({**config, "client-secret": secret_id, "client_secret": "legacy-value"})
    relation_id = _request_client(harness)

    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert "client_secret_id" not in harness.get_relation_data(relation_id, harness.charm.app)

    harness.grant_secret(secret_id, harness.charm.app)
    harness.charm.on.update_status.emit()

    assert _shared_secret(harness, relation_id) == "granted-later"
    assert isinstance(harness.charm.unit.status, ActiveStatus)


def test_secret_rotation_updates_existing_clients_without_replacing_the_shared_secret(
    harness: Harness, config: Dict
) -> None:
    secret_id = harness.add_user_secret({"client-secret": "first-value"})
    harness.grant_secret(secret_id, harness.charm.app)
    harness.update_config({**config, "client-secret": secret_id})
    relation_id = _request_client(harness)
    shared_id = harness.get_relation_data(relation_id, harness.charm.app)["client_secret_id"]

    harness.set_secret_content(secret_id, {"client-secret": "rotated-value"})

    assert _shared_secret(harness, relation_id) == "rotated-value"
    assert (
        harness.get_relation_data(relation_id, harness.charm.app)["client_secret_id"] == shared_id
    )


def test_legacy_development_credentials_still_work_without_a_secret_uri(
    harness: Harness, config: Dict
) -> None:
    harness.update_config({**config, "client_secret": "development-only"})

    relation_id = _request_client(harness)

    assert _shared_secret(harness, relation_id) == "development-only"


def test_removing_a_client_does_not_republish_to_the_departing_relation(
    harness: Harness, config: Dict
) -> None:
    harness.update_config(config)
    relation_id = _request_client(harness)

    harness.remove_relation(relation_id)

    assert isinstance(harness.charm.unit.status, BlockedStatus)
    assert harness.charm.unit.status.message == "Missing client relation"
