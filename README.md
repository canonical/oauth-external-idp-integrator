# OAuth External IDP Integrator

[![CharmHub Badge](https://charmhub.io/oauth-external-idp-integrator/badge.svg)](https://charmhub.io/oauth-external-idp-integrator)

## Description

This charm is used to provide the [oauth interface](https://github.com/canonical/charm-relation-interfaces/tree/main/interfaces/oauth/v0) to OAuth enabled charms which use an external OAuth provider (example: Google).

## Usage

### Deployment

For the `oauth-external-idp-integrator` charm to be operative you need to deploy it, configure it and relate to a charm that consumes the oauth interface (ex: kafka).:
```commandline
juju deploy oauth-external-idp-integrator
juju config oauth-external-idp-integrator \
    issuer_url=https://accounts.google.com \
    authorization_endpoint=https://accounts.google.com/o/oauth2/auth \
    introspection_endpoint=https://oauth2.googleapis.com/tokeninfo \
    jwks_endpoint=https://www.googleapis.com/oauth2/v3/certs \
    scope="openid profile email" \
    token_endpoint=https://oauth2.googleapis.com/token \
    userinfo_endpoint=https://www.googleapis.com/oauth2/v1/userinfo
# relating it to kafka (for example) 
juju relate oauth-external-idp-integrator kafka-k8s
```

### Client credentials

For production, keep the client secret in a Juju user secret, not the legacy
`client_secret` string option. This requires Juju 3.3 or later.

Provision the secret from your secret manager (for example Vault) with a
`client-secret` content key, grant it to `oauth-external-idp-integrator`, then
configure only its URI:

```commandline
juju grant-secret <secret-uri> oauth-external-idp-integrator
juju config oauth-external-idp-integrator \
    client_id=<public-client-id> client-secret=<secret-uri>
```

The charm reads the credential through Juju's secret API and shares it with
OAuth clients using the interface's relation-granted secret. The raw credential
is never written to ordinary charm configuration or relation data.

An unreadable secret, missing `client-secret` key, or blank value blocks the
charm; it never falls back to `client_secret` when a secret URI is configured.
Secret changes update the client credential, and `update-status` retries a grant
that arrived after the configuration. The legacy option remains available for
development when `client-secret` is unset.


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this
charm following best practice guidelines, and
[CONTRIBUTING.md](https://github.com/canonical/oauth-external-idp-integrator/blob/main/CONTRIBUTING.md) for developer
guidance.
