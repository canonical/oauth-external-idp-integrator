#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""A Juju charm for integrating OAuth enabled charms with and external IdP."""

import logging
from typing import Any

from charms.hydra.v0.oauth import ClientCreatedEvent, OAuthProvider
from ops.charm import (
    CharmBase,
    ConfigChangedEvent,
    EventBase,
    RelationBrokenEvent,
    RelationCreatedEvent,
)
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus

logger = logging.getLogger(__name__)


class OAuthIdpIntegratorCharm(CharmBase):
    """Charm the service."""

    _relation_name = "oauth"

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.oauth = OAuthProvider(self)

        # Charm events
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)

        self.framework.observe(self.on.oauth_relation_created, self._on_oauth_relation_created)
        self.framework.observe(self.on.oauth_relation_broken, self._on_oauth_relation_broken)
        self.framework.observe(self.oauth.on.client_created, self._on_client_created)

    def _on_oauth_relation_created(self, event: RelationCreatedEvent) -> None:
        """Oauth relation created handler."""
        self._configure_relation()
        self._on_update_status(event)

    def _on_oauth_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Oauth relation broken handler."""
        self._on_update_status(event)

    def _on_client_created(self, event: ClientCreatedEvent) -> None:
        """Oauth client created handler."""
        self.oauth.set_client_credentials_in_relation_data(
            event.relation_id, "client_id", "client_secret"
        )

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Handle config change."""
        self._configure_relation()
        self._on_update_status(event)

    def _on_update_status(self, event: EventBase) -> None:
        """Set the unit status."""
        client_available = self._client_available()
        valid_config, key = self._validate_config()
        if not valid_config:
            self.unit.status = BlockedStatus(f"Missing required configuration: {key}")
        elif not client_available:
            self.unit.status = BlockedStatus("Missing client relation")
        else:
            self.unit.status = ActiveStatus()

    def _client_available(self):
        """Check if the client relation is still available."""
        for relation in self.model.relations[OAuthIdpIntegratorCharm._relation_name]:
            if relation.data[self.app]:
                return True
        return False

    def _configure_relation(self) -> None:
        """Configure oauth relation."""
        client_related = bool(self.model.relations[OAuthIdpIntegratorCharm._relation_name])
        valid_config, _ = self._validate_config()
        if client_related and valid_config:
            self.oauth.set_provider_info_in_relation_data(
                issuer_url=self.config.get("issuer_url"),
                authorization_endpoint=self.config["authorization_endpoint"],
                token_endpoint=self.config["token_endpoint"],
                introspection_endpoint=self.config["introspection_endpoint"],
                userinfo_endpoint=self.config["userinfo_endpoint"],
                jwks_endpoint=self.config["jwks_endpoint"],
                scope=self.config["scope"],
            )

    def _validate_config(self) -> (bool, str):
        """Validate the user provided config."""
        mandatory_fields = [
            "issuer_url",
            "authorization_endpoint",
            "userinfo_endpoint",
            "token_endpoint",
            "introspection_endpoint",
            "jwks_endpoint",
            "scope",
        ]
        for key in mandatory_fields:
            if not self.config.get(key, None):
                return False, key
        return True, ""


if __name__ == "__main__":
    main(OAuthIdpIntegratorCharm)
