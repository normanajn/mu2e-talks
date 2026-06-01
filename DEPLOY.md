# Mu2eTalks Deployment

Mu2eTalks supports Docker Compose for a production-like local host and Helm for OKD.

## Required Secrets

- `DJANGO_SECRET_KEY`: strong Django secret key.
- `MU2E_INITIAL_ADMIN_PASSWORD`: bootstrap password for the initial admin account.
- `POSTGRES_PASSWORD`: required for the Compose Postgres stack.
- `OIDC_CLIENT_SECRET`: required only when OIDC SSO is enabled.

The default bootstrap admin is:

- Username: `mu2e-admin`
- Email: `mu2e-admin@fnal.gov`

Override with `MU2E_INITIAL_ADMIN_USERNAME` and `MU2E_INITIAL_ADMIN_EMAIL`.

## Docker Compose

```bash
cp .env.example .env
# Edit .env with POSTGRES_PASSWORD, DJANGO_SECRET_KEY, MU2E_INITIAL_ADMIN_PASSWORD, MU2E_HOSTNAME
docker compose up --build -d
docker compose logs -f web
```

Compose runs:

- `db`: PostgreSQL 16
- `web`: Django/Gunicorn
- `caddy`: HTTPS reverse proxy and static/media serving

## OKD / Helm

Create a private values file:

```yaml
image:
  repository: docker.io/normanajn/mu2e-talks-web
  tag: latest

route:
  hostname: mu2e-talks.fnal.gov

django:
  settingsModule: mu2e_talks.settings.prod
  secretKey: "<set privately>"
  allowedHosts: "mu2e-talks.fnal.gov"
  disableLocalSignup: "1"
  localLoginEnabled: "0"
  initialAdminUsername: mu2e-admin
  initialAdminEmail: mu2e-admin@fnal.gov
  initialAdminPassword: "<set privately>"

oidc:
  providerUrl: "<oidc discovery or realm url>"
  clientId: "mu2e-talks"
  clientSecret: "<set privately>"
```

Deploy:

```bash
helm upgrade --install mu2e-talks ./helm/simple \
  -n mu2e-talks --create-namespace \
  -f my-values.yaml
```

Verify:

```bash
oc get pods -n mu2e-talks
oc get route -n mu2e-talks
oc logs deployment/web -n mu2e-talks --tail=100
```
