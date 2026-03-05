# 🔒 Secrets Management & Configuration Guide

This guide explains how your application manages configuration and secrets securely across different environments.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Configuration Fallback Mechanism](#configuration-fallback-mechanism)
3. [Local Development Setup](#local-development-setup)
4. [Google Cloud Secrets Setup](#google-cloud-secrets-setup)
5. [Deploying to Cloud Run](#deploying-to-cloud-run)
6. [IAM Permissions Explained](#iam-permissions-explained)
7. [Security Best Practices](#security-best-practices)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Overview

Your FastAPI application uses a **secure fallback mechanism** for configuration:

```
Priority Order (highest to lowest):
1. Environment Variables (Cloud Run)
2. .env file (local development)
3. .env-model file (local model config)
4. Default values in code
```

### Key Principles

- ✅ **Production**: Secrets stored in Google Secret Manager, accessed via Cloud Run
- ✅ **Local Development**: Secrets in `.env` files (never committed to git)
- ✅ **No Hardcoding**: Never hardcode secrets in code or deploy scripts
- ✅ **Automatic Fallback**: Works seamlessly in both environments

---

## Configuration Fallback Mechanism

### How It Works

The application uses Pydantic Settings with automatic environment variable precedence:

```python
# app/core/settings.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env-model"),  # Fallback files
        env_file_encoding="utf-8",
        extra="ignore",
    )
    
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")
    database_url_override: str | None = Field(default=None, alias="DATABASE_URL")
    # ... other settings
```

### Loading Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Check Environment Variables                              │
│    └─ Set by Cloud Run: --set-env-vars, --set-secrets       │
│                                                              │
│ 2. If not found, check .env file                            │
│    └─ Only exists in local development                      │
│                                                              │
│ 3. If not found, check .env-model file                      │
│    └─ Only exists in local development                      │
│                                                              │
│ 4. If not found, use default value                          │
│    └─ Defined in Field(default=...)                         │
└─────────────────────────────────────────────────────────────┘
```

### Environment Detection

The application automatically detects the environment:

- **Cloud Run**: Environment variables are set → uses those (no `.env` files in container)
- **Local Development**: No env vars → falls back to `.env` files

---

## Local Development Setup

### Step 1: Create `.env` File

```bash
cp .env.example .env
```

Edit `.env` with your local values:

```bash
# App
APP_NAME=Thesis Agent Backend
ENVIRONMENT=local
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/dbname
# OR use individual components:
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=mike
POSTGRES_PASSWORD=mypassword
POSTGRES_DB=postgres-db-vector

# CORS (for local frontend)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Step 2: Create `.env-model` File

```bash
cp .env-model.example .env-model
```

Edit `.env-model` with your API keys:

```bash
# Gemini / model settings
GEMINI_API_KEY=your-actual-api-key-here
GEMINI_MODEL=gemini-2.5-flash
```

### Step 3: Verify Configuration

```bash
# Activate virtual environment
source venv/bin/activate

# Start the development server
uvicorn app.main:app --reload

# In another terminal, test
curl http://localhost:8000/health
```

### Important Notes

- ⚠️ **Never commit** `.env` or `.env-model` to git (already in `.gitignore`)
- ✅ Always use `.env.example` and `.env-model.example` as templates
- 🔒 Keep your API keys secure and rotate them periodically

---

## Google Cloud Secrets Setup

### Prerequisites

1. **Install Google Cloud SDK**:
   ```bash
   # macOS
   brew install google-cloud-sdk
   
   # Or download from: https://cloud.google.com/sdk/docs/install
   ```

2. **Authenticate with Google Cloud**:
   ```bash
   gcloud auth login
   ```

3. **Set Your Project**:
   ```bash
   gcloud config set project fastapi-adai-420420
   ```

4. **Enable Required APIs**:
   ```bash
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable run.googleapis.com
   gcloud services enable artifactregistry.googleapis.com
   ```

### Creating Secrets

#### Option 1: Use the Automated Script (Recommended)

```bash
./setup-secrets.sh
```

This script will:
1. Create secrets in Google Secret Manager
2. Configure IAM permissions automatically
3. Verify the setup

#### Option 2: Manual Setup

##### Create GEMINI_API_KEY Secret

```bash
# Store your API key in a temporary file (secure method)
echo -n "your-gemini-api-key" > /tmp/gemini_key.txt

# Create the secret
gcloud secrets create GEMINI_API_KEY \
  --data-file="/tmp/gemini_key.txt" \
  --replication-policy="automatic"

# Clean up temporary file
rm /tmp/gemini_key.txt
```

##### Create DATABASE_URL Secret

```bash
# Store your database URL in a temporary file
echo -n "postgresql+psycopg2://user:pass@host:5432/db" > /tmp/db_url.txt

# Create the secret
gcloud secrets create DATABASE_URL \
  --data-file="/tmp/db_url.txt" \
  --replication-policy="automatic"

# Clean up temporary file
rm /tmp/db_url.txt
```

### Configuring IAM Permissions

**YES, you MUST configure IAM permissions** for Cloud Run to access secrets.

```bash
# Get your project number
PROJECT_NUMBER=$(gcloud projects describe fastapi-adai-420420 \
  --format="value(projectNumber)")

# Grant Cloud Run access to GEMINI_API_KEY
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Grant Cloud Run access to DATABASE_URL
gcloud secrets add-iam-policy-binding DATABASE_URL \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Why IAM Binding is Required

The IAM policy binding is **essential** because:

1. **Access Control**: Cloud Run runs with a service account that needs explicit permission
2. **Security**: Prevents unauthorized access to secrets
3. **Least Privilege**: Only the specific service account can access the secrets
4. **Audit Trail**: Google logs all secret access for security monitoring

Without this command, Cloud Run will get **"Permission Denied"** errors when trying to access secrets.

### Verifying Secrets

```bash
# List all secrets
gcloud secrets list

# View secret metadata (not the value)
gcloud secrets describe GEMINI_API_KEY

# View secret versions
gcloud secrets versions list GEMINI_API_KEY

# View IAM permissions
gcloud secrets get-iam-policy GEMINI_API_KEY

# Access secret value (requires permission)
gcloud secrets versions access latest --secret=GEMINI_API_KEY
```

---

## Deploying to Cloud Run

### Step 1: Configure `deploy.sh`

The `deploy.sh` script is already configured to use secrets from Secret Manager:

```bash
# Secret Manager secret names (NOT the actual values!)
GEMINI_API_KEY_SECRET="GEMINI_API_KEY"
DATABASE_URL_SECRET="DATABASE_URL"
```

### Step 2: Deploy

```bash
./deploy.sh
```

The script will:
1. Build Docker image
2. Push to Artifact Registry
3. Deploy to Cloud Run with:
   - Environment variables: `--set-env-vars`
   - Secrets: `--set-secrets` (references Secret Manager)

### How Secrets Are Mounted

In `deploy.sh`, the `--set-secrets` flag works as follows:

```bash
--set-secrets="GEMINI_API_KEY=GEMINI_API_KEY:latest,DATABASE_URL=DATABASE_URL:latest"
```

Format: `ENV_VAR_NAME=SECRET_MANAGER_NAME:version`

- `ENV_VAR_NAME`: Environment variable name in your application
- `SECRET_MANAGER_NAME`: Name of secret in Secret Manager
- `version`: Version of secret (usually `latest`)

Cloud Run automatically:
1. Fetches the secret value from Secret Manager
2. Injects it as an environment variable
3. Makes it available to your application

### Deployment Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Build Docker Image                                       │
│    └─ Dockerfile (no secrets included)                      │
│                                                              │
│ 2. Push to Artifact Registry                                │
│    └─ Image in GCP registry                                 │
│                                                              │
│ 3. Deploy to Cloud Run                                      │
│    ├─ --set-env-vars: Non-sensitive config                  │
│    └─ --set-secrets: References to Secret Manager           │
│                                                              │
│ 4. Cloud Run Runtime                                        │
│    ├─ Fetches secrets from Secret Manager                   │
│    ├─ Injects as environment variables                      │
│    └─ Application reads via os.environ                      │
└─────────────────────────────────────────────────────────────┘
```

---

## IAM Permissions Explained

### Service Accounts in Cloud Run

By default, Cloud Run uses the **Compute Engine default service account**:

```
{PROJECT_NUMBER}-compute@developer.gserviceaccount.com
```

### Required Permissions

For Cloud Run to access secrets, this service account needs:

- **Role**: `roles/secretmanager.secretAccessor`
- **Applied to**: Each secret you want to use

### Permission Scope

The `secretAccessor` role allows:
- ✅ Read secret values
- ✅ List secret versions
- ❌ Create or delete secrets (protected)
- ❌ Modify IAM policies (protected)

### Custom Service Accounts (Optional)

For better security, you can create a custom service account:

```bash
# Create custom service account
gcloud iam service-accounts create cloud-run-adai \
  --display-name="Cloud Run AdAi Service Account"

# Grant secret access
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:cloud-run-adai@fastapi-adai-420420.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Deploy with custom service account
gcloud run deploy adai-fastapi \
  --service-account=cloud-run-adai@fastapi-adai-420420.iam.gserviceaccount.com \
  ...
```

---

## Security Best Practices

### ✅ DO

1. **Use Secret Manager** for production secrets
2. **Keep `.env` files local** (never commit to git)
3. **Rotate secrets periodically** (every 90 days recommended)
4. **Use least privilege** IAM permissions
5. **Enable secret versioning** for rollback capability
6. **Monitor secret access** via Cloud Logging
7. **Use different secrets** for different environments (dev/staging/prod)

### ❌ DON'T

1. **Never hardcode** secrets in code
2. **Never commit** `.env` files to git
3. **Never log** secret values
4. **Never pass secrets** as command-line arguments
5. **Never store secrets** in Docker images
6. **Never share secrets** via email or chat
7. **Never use production secrets** in development

### Secret Rotation

To rotate a secret:

```bash
# Create new version
echo -n "new-secret-value" | gcloud secrets versions add GEMINI_API_KEY --data-file=-

# Cloud Run automatically uses "latest" version
# No redeployment needed if using :latest in --set-secrets

# Optional: Disable old version
gcloud secrets versions disable 1 --secret=GEMINI_API_KEY
```

### Audit Logging

View who accessed secrets:

```bash
gcloud logging read \
  "resource.type=secretmanager.googleapis.com/Secret
   AND protoPayload.methodName=AccessSecretVersion" \
  --limit=50 \
  --format=json
```

---

## Troubleshooting

### Issue: "Permission Denied" on Secret Access

**Problem**: Cloud Run can't access secrets

**Solution**:
```bash
# Check IAM bindings
gcloud secrets get-iam-policy GEMINI_API_KEY

# If missing, add binding
PROJECT_NUMBER=$(gcloud projects describe fastapi-adai-420420 --format="value(projectNumber)")
gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# Redeploy
./deploy.sh
```

### Issue: Environment Variables Not Loading Locally

**Problem**: Application can't find `.env` file

**Solution**:
```bash
# Check if .env exists
ls -la .env

# Check file contents (be careful not to share)
cat .env

# Verify Python can read it
python -c "from app.core.settings import get_settings; print(get_settings().gemini_api_key)"
```

### Issue: Secrets Not Updated in Cloud Run

**Problem**: Changed secret but app still uses old value

**Solution**:
```bash
# If using versioned secrets (e.g., :1, :2), redeploy
./deploy.sh

# If using :latest, secret should update automatically
# Force new revision:
gcloud run services update adai-fastapi \
  --region=us-central1 \
  --update-env-vars="LAST_UPDATED=$(date +%s)"
```

### Issue: Docker Build Includes `.env` File

**Problem**: Secrets leaked in Docker image

**Solution**:
```bash
# Check .dockerignore exists
cat .dockerignore

# Add to .dockerignore:
echo ".env" >> .dockerignore
echo ".env-model" >> .dockerignore

# Rebuild image
./deploy.sh
```

### Debug: Check What Cloud Run Sees

```bash
# SSH into Cloud Run container (for debugging only)
gcloud run services proxy adai-fastapi --port=8080

# View logs
gcloud logging read \
  "resource.type=cloud_run_revision 
   AND resource.labels.service_name=adai-fastapi" \
  --limit=50 \
  --format=json
```

---

## FAQ

### Q: Can I use different secret names in Cloud Run vs locally?

**A**: Yes! The application uses environment variable names (e.g., `GEMINI_API_KEY`). In Cloud Run, these come from Secret Manager. Locally, they come from `.env` files.

### Q: How do I add more secrets?

**A**: 
1. Create secret in Secret Manager: `gcloud secrets create MY_NEW_SECRET --data-file=...`
2. Add IAM binding for Cloud Run
3. Update `deploy.sh` to reference it in `--set-secrets`
4. Add to `.env.example` and `.env` for local development
5. Update `app/core/settings.py` if needed

### Q: What if I accidentally commit a secret to git?

**A**: 
1. **Immediately rotate the secret** (create new value)
2. Remove from git history (use `git filter-branch` or BFG Repo-Cleaner)
3. Force push to remote
4. Notify your team
5. Review git security practices

### Q: How much does Secret Manager cost?

**A**: 
- First 6 secret versions: Free
- Additional versions: $0.06 per version per month
- Secret access: $0.03 per 10,000 accesses
- Most small projects: **Under $1/month**

Pricing details: https://cloud.google.com/secret-manager/pricing

### Q: Can I use AWS Secrets Manager or HashiCorp Vault instead?

**A**: Yes, but you'll need to:
1. Modify `app/core/settings.py` to fetch from your secret provider
2. Update deployment scripts
3. Handle authentication differently

For Google Cloud Run, GCP Secret Manager is the most native solution.

### Q: Do secrets persist after container restarts?

**A**: Yes! Secrets are fetched from Secret Manager on each container start. Cloud Run handles this automatically.

### Q: How do I use different secrets for staging vs production?

**A**: Best practice:
```bash
# Create environment-specific secrets
gcloud secrets create GEMINI_API_KEY_STAGING --data-file=...
gcloud secrets create GEMINI_API_KEY_PROD --data-file=...

# Deploy to staging
gcloud run deploy adai-fastapi-staging \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY_STAGING:latest"

# Deploy to production
gcloud run deploy adai-fastapi-prod \
  --set-secrets="GEMINI_API_KEY=GEMINI_API_KEY_PROD:latest"
```

---

## Summary

### Configuration Loading Order

1. **Cloud Run**: Environment variables from `--set-env-vars` and `--set-secrets`
2. **Local Development**: `.env` and `.env-model` files
3. **Fallback**: Default values in code

### Key Commands

```bash
# Local Development
cp .env.example .env
cp .env-model.example .env-model
# Edit files with your secrets
uvicorn app.main:app --reload

# Production Setup
./setup-secrets.sh          # One-time setup
./deploy.sh                 # Deploy to Cloud Run

# Manage Secrets
gcloud secrets create SECRET_NAME --data-file=/path/to/file
gcloud secrets versions add SECRET_NAME --data-file=/path/to/file
gcloud secrets versions access latest --secret=SECRET_NAME
gcloud secrets delete SECRET_NAME
```

### Security Checklist

- [ ] `.env` and `.env-model` in `.gitignore`
- [ ] Secrets created in Secret Manager
- [ ] IAM permissions configured
- [ ] No secrets hardcoded in code
- [ ] `.dockerignore` excludes `.env` files
- [ ] Secrets rotated periodically
- [ ] Audit logging enabled
- [ ] Different secrets for different environments

---

## Additional Resources

- [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Run Secrets Guide](https://cloud.google.com/run/docs/configuring/secrets)
- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [12-Factor App Config](https://12factor.net/config)

---

**Last Updated**: March 2026  
**Maintained By**: AdAi-FastAPI Team  
**Questions?** Open an issue on GitHub
