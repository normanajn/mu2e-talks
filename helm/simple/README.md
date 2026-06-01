# mu2e-talks-simple Helm Chart

Single-container OKD deployment for Mu2eTalks using SQLite PVC storage and optional OKD Route TLS.

## Install

```bash
helm upgrade --install mu2e-talks ./helm/simple \
  -n mu2e-talks --create-namespace \
  -f my-values.yaml
```

## Required Private Values

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
  initialAdminUsername: mu2e-admin
  initialAdminEmail: mu2e-admin@fnal.gov
  initialAdminPassword: "<set privately>"

oidc:
  providerUrl: "<oidc discovery or realm url>"
  clientId: "mu2e-talks"
  clientSecret: "<set privately>"
```

## Verify

```bash
oc get pods -n mu2e-talks
oc get route -n mu2e-talks
oc logs deployment/web -n mu2e-talks --tail=100
```
