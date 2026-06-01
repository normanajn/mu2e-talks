# Cert-Manager Initialization and Activation

The Mu2eTalks Helm chart can request an HTTPS certificate from cert-manager and
attach the resulting TLS secret to the OKD Route. Certificate initialization is
a two-step process because OKD rejects a Route that references a TLS secret
before that secret exists.

These instructions assume:

- The OKD project is `mu2e-talks`.
- The Helm release is named `mu2e-talks`.
- The public hostname is `mu2e-talks.fnal.gov`.
- The cluster provides the `incommon-acme` `ClusterIssuer`.
- The private deployment settings are stored in the ignored `my-values.yaml`
  file at the repository root.

## 1. Verify the ClusterIssuer

Log in to OKD and confirm that the issuer is available:

```bash
oc login https://api.<your-okd-cluster>:6443
oc project mu2e-talks
oc get clusterissuer incommon-acme
```

If the issuer is missing, contact the OKD administrator before continuing.

## 2. Initialize Certificate Issuance

Set the following values in `my-values.yaml`:

```yaml
route:
  hostname: mu2e-talks.fnal.gov

certManager:
  enabled: true
  clusterIssuer: incommon-acme
  secretName: mu2e-talks-tls
  externalCertificate: false
```

The `externalCertificate: false` setting is required during initialization. It
allows Helm to create the Route and the cert-manager `Certificate` resource
without asking the Route to use a secret that does not exist yet.

Deploy the release:

```bash
helm upgrade --install mu2e-talks ./helm/simple \
  --namespace mu2e-talks \
  --values my-values.yaml
```

## 3. Wait for the TLS Secret

Check the certificate request and generated secret:

```bash
oc get certificate,certificaterequest,secret,route,pods -n mu2e-talks
oc describe certificate mu2e-talks -n mu2e-talks
```

Wait until the output shows:

```text
certificate.cert-manager.io/mu2e-talks   True   mu2e-talks-tls
secret/mu2e-talks-tls                    kubernetes.io/tls
```

The certificate description should report a `Ready` condition with
`Status: True`.

## 4. Activate the Certificate on the Route

Once `secret/mu2e-talks-tls` exists, update `my-values.yaml`:

```yaml
certManager:
  enabled: true
  clusterIssuer: incommon-acme
  secretName: mu2e-talks-tls
  externalCertificate: true
```

Apply the final Helm update:

```bash
helm upgrade --install mu2e-talks ./helm/simple \
  --namespace mu2e-talks \
  --values my-values.yaml
```

Verify that the Route references the TLS secret:

```bash
oc get route web -n mu2e-talks \
  -o jsonpath='{.spec.tls.externalCertificate.name}{"\n"}'
```

Expected output:

```text
mu2e-talks-tls
```

Verify that the login page is available through HTTPS:

```bash
curl --head --location https://mu2e-talks.fnal.gov/accounts/login/
```

The response should include:

```text
HTTP/1.1 200 OK
```

## Troubleshooting

If Helm reports:

```text
spec.tls.externalCertificate: Not found: "secrets \"mu2e-talks-tls\" not found"
```

set `certManager.externalCertificate` to `false`, run the Helm deployment, wait
for cert-manager to create `secret/mu2e-talks-tls`, and then repeat the
activation step.

For additional cert-manager diagnostics:

```bash
oc get clusterissuer incommon-acme
oc describe certificate mu2e-talks -n mu2e-talks
oc get certificaterequest -n mu2e-talks
```

After activation, cert-manager renews the certificate automatically. The Route
continues to reference `mu2e-talks-tls`, so renewed certificate data is used
without repeating the initialization procedure.
