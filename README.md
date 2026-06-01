# Mu2eTalks

Mu2eTalks is a Django web application for managing conference talks given by members of the Mu2e collaboration. It tracks conferences, talk assignments, practice-talk status, final approval, whether a talk has been given, comments, and searchable/exportable reports.

## Features

- **Talk tracking**: conference title/dates/URL, talk title, DocDB number, assigned speaker, practice date, practice complete, final approval, complete/given, Markdown comments, and draft/active status.
- **Roles**:
  - User: create draft talks and edit talks assigned to them.
  - IB Rep: create, edit, assign, and activate talks.
  - Spokesperson: create, edit, assign, activate, and delete talks.
  - Admin: full application and user-management access.
- **Reports**: all authenticated users can search all talks, including boolean full-text search with `AND`, `OR`, `XOR`, quoted phrases, field filters, preview, and TXT/Markdown/CSV/JSON/XLSX/PDF exports.
- **Authentication**: local auth plus optional OIDC SSO through django-allauth.
- **Roster management**: institution and collaboration-member CSV imports, separate login and contact emails, first-login roster matching, institution editing, and admin editing of imported user metadata.
- **Deployment**: Docker Compose and Helm/OKD deployment paths.

## Local Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python manage.py migrate
MU2E_INITIAL_ADMIN_PASSWORD=changeme python manage.py seed_admin
python manage.py runserver
```

Open <http://localhost:8000/> and log in as `mu2e-admin@fnal.gov` with the password set in `MU2E_INITIAL_ADMIN_PASSWORD`.

## Helper Scripts

The scripts load the repository-level `.env` file and can be run from any working directory:

```bash
./scripts/start-mu2e-talks
./scripts/stop-mu2e-talks
./scripts/start-mu2e-talks-docker
./scripts/stop-mu2e-talks-docker
```

PowerShell equivalents are available for Windows:

```powershell
.\scripts\start-mu2e-talks.ps1
.\scripts\stop-mu2e-talks.ps1
.\scripts\start-mu2e-talks-docker.ps1
.\scripts\stop-mu2e-talks-docker.ps1
```

## Docker Compose

```bash
cp .env.example .env
# Set POSTGRES_PASSWORD, DJANGO_SECRET_KEY, MU2E_INITIAL_ADMIN_PASSWORD, MU2E_HOSTNAME
docker compose up --build
```

The production-like Compose stack runs Postgres, the Django web container, and Caddy.

## OKD / Helm

Use the simple chart for the OKD single-container deployment:

```bash
helm upgrade --install mu2e-talks ./helm/simple \
  -n mu2e-talks --create-namespace \
  -f my-values.yaml
```

Set `django.secretKey`, `django.initialAdminPassword`, image values, route hostname, and OIDC values in a private values file. Do not commit real secrets.

For subsequent releases, build the Docker image, push it, apply the Helm
upgrade, restart the deployment, and wait for readiness with:

```bash
./scripts/deploy-okd.sh
```

The script uses the exact Git tag on `HEAD` as the image tag. Run
`./scripts/deploy-okd.sh --help` for repository, namespace, values file, and
timeout overrides.

## Verification

```bash
python3 manage.py check
python3 manage.py makemigrations --check --dry-run
python3 -m pytest -q
```

Current expected result: `75 passed`.
