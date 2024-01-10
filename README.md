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


## Contributing

Please see the [Juju SDK docs](https://juju.is/docs/sdk) for guidelines on enhancements to this
charm following best practice guidelines, and
[CONTRIBUTING.md](https://github.com/canonical/oauth-external-idp-integrator/blob/main/CONTRIBUTING.md) for developer
guidance.
