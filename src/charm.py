#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.

"""A Juju charm for integrating OAuth enabled charms with and external IdP."""

import logging
from typing import Any, List, Optional

from charms.hydra.v0.oauth import (
    CLIENT_SECRET_FIELD,
    ClientCreatedEvent,
    DataValidationError,
    OAuthProvider,
)
from ops.charm import (
    CharmBase,
    ConfigChangedEvent,
    EventBase,
    RelationBrokenEvent,
    RelationCreatedEvent,
    SecretChangedEvent,
)
from ops.main import main
from ops.model import ActiveStatus, BlockedStatus, ModelError, SecretNotFoundError

logger = logging.getLogger(__name__)

_CLIENT_SECRET_LABEL = "configured-client-secret"


class OAuthIdpIntegratorCharm(CharmBase):
    """Charm the service."""

    _relation_name = "oauth"

    def __init__(self, *args: Any) -> None:
        super().__init__(*args)
        self.oauth = OAuthProvider(self)

        # Charm events
        self.framework.observe(self.on.config_changed, self._on_config_changed)
        self.framework.observe(self.on.update_status, self._on_update_status)
        self.framework.observe(self.on.secret_changed, self._on_secret_changed)

        self.framework.observe(self.on.oauth_relation_created, self._on_oauth_relation_created)
        self.framework.observe(self.on.oauth_relation_broken, self._on_oauth_relation_broken)
        self.framework.observe(self.oauth.on.client_created, self._on_client_created)

    def _on_oauth_relation_created(self, event: RelationCreatedEvent) -> None:
        """Oauth relation created handler."""
        self._on_update_status(event)

    def _on_oauth_relation_broken(self, event: RelationBrokenEvent) -> None:
        """Oauth relation broken handler."""
        self._on_update_status(event)

    def _on_client_created(self, event: ClientCreatedEvent) -> None:
        """Oauth client created handler."""
        self._publish_client_credentials(event.relation_id)

    def _get_client_secret(self) -> Optional[str]:
        """Resolve the configured secret without falling back after a failed read."""
        secret_uri = self.config.get("client-secret")
        if not secret_uri:
            return self.config.get("client_secret")
        try:
            secret = self.model.get_secret(id=secret_uri, label=_CLIENT_SECRET_LABEL)
            value = secret.get_content(refresh=True).get("client-secret")
        except ModelError:
            logger.warning("Cannot read the configured client-secret Juju secret")
            return None
        return value if value and value.strip() else None

    def _publish_client_credentials(self, relation_id: int) -> None:
        """Create or refresh credentials only when a configured secret is readable."""
        if not self.unit.is_leader():
            return
        client_secret = self._get_client_secret()
        if not client_secret:
            self.unit.status = BlockedStatus("Cannot read a non-empty client-secret")
            return
        relation = self.model.get_relation(self._relation_name, relation_id)
        if not relation:
            return
        client_id = self.config["client_id"]
        data = relation.data[self.app]
        if data.get("client_id") == client_id and data.get("client_secret_id"):
            try:
                # This secret is ours: refresh=True is only for consumers.
                shared = self.model.get_secret(id=data["client_secret_id"]).peek_content()
            except SecretNotFoundError:
                pass
            else:
                if shared.get(CLIENT_SECRET_FIELD) == client_secret:
                    return
        self.oauth.set_client_credentials_in_relation_data(relation_id, client_id, client_secret)

    def _on_secret_changed(self, event: SecretChangedEvent) -> None:
        """Propagate a new revision of the configured credential to OAuth clients."""
        if event.secret.label == _CLIENT_SECRET_LABEL:
            self._on_update_status(event)

    def _on_config_changed(self, event: ConfigChangedEvent) -> None:
        """Handle config change."""
        self._on_update_status(event)

    def _on_update_status(self, event: EventBase) -> None:
        """Reconcile relations and retry secret grants before setting status."""
        departing_id = event.relation.id if isinstance(event, RelationBrokenEvent) else None
        if departing_id is None:
            self._configure_relation()
        client_available = self._client_available(exclude_relation_id=departing_id)
        missing_config = self._validate_config()
        if bool(missing_config):
            self.unit.status = BlockedStatus(f"Missing required configurations: {missing_config}")
        elif not client_available:
            self.unit.status = BlockedStatus("Missing client relation")
        else:
            self.unit.status = ActiveStatus()

    def _client_available(self, exclude_relation_id: Optional[int] = None) -> bool:
        """Check if the client relation is still available."""
        for relation in self.model.relations[OAuthIdpIntegratorCharm._relation_name]:
            if relation.id != exclude_relation_id and relation.data[self.app]:
                return True
        return False

    def _configure_relation(self) -> None:
        """Configure oauth relation."""
        client_related = bool(self.model.relations[OAuthIdpIntegratorCharm._relation_name])
        missing_config = self._validate_config()
        if client_related and not bool(missing_config):
            self.oauth.set_provider_info_in_relation_data(
                issuer_url=self.config["issuer_url"],
                authorization_endpoint=self.config["authorization_endpoint"],
                token_endpoint=self.config["token_endpoint"],
                introspection_endpoint=self.config["introspection_endpoint"],
                userinfo_endpoint=self.config["userinfo_endpoint"],
                jwks_endpoint=self.config["jwks_endpoint"],
                scope=self.config["scope"],
                jwt_access_token=bool(self.config["jwt_access_token"]),
            )
            for relation in self.model.relations[self._relation_name]:
                try:
                    client_config = self.oauth.get_client_config(relation)
                except DataValidationError:
                    logger.warning("Ignoring invalid OAuth client configuration")
                    continue
                if client_config:
                    self._publish_client_credentials(relation.id)

    def _validate_config(self) -> List[str]:
        """Validate the user provided config."""
        missing_fields = []
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
                missing_fields.append(key)
        if self.config.get("client-secret") and not self._get_client_secret():
            missing_fields.append(
                "client-secret (unreadable or missing a non-empty client-secret key)"
            )
        return missing_fields


if __name__ == "__main__":
    main(OAuthIdpIntegratorCharm)
