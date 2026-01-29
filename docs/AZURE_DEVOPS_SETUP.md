# Azure Deployment & Azure DevOps (Azure Repos) Setup

This guide explains how to configure and deploy this repository from **Azure Repos** using **Azure Pipelines** into **Azure hosting**.

It is intentionally **implementation-aligned** with this repo’s current structure:
- Backend (Python/FastAPI): `backend/` (entrypoint: `src.web.app_fastapi:app`)
- Frontend (Vite/React): build from repo root (`npm run build`) → output `dist/`
- Database: **Neo4j Aura** (external managed service; recommended for Azure)

## 1) Target architecture (your selection: SWA + App Service + Front Door, public)

You selected: **A + Aura + Public**

- **Frontend**: Azure Static Web Apps (SWA)
- **Backend**: Azure App Service (Python, Linux)
- **Routing**: Azure Front Door (Standard/Premium)
  - Route `/*` → SWA origin
  - Route `/api/*` → Backend origin

This preserves the frontend’s current assumption that API requests go to **`/api`** (relative path) and avoids browser CORS complexity because the browser calls the **same hostname** (Front Door) for both UI and API.

### Option B: Single App Service (co-host)
If you choose to host the frontend and backend together, you must ensure that requests to `/api/*` reach the backend and the static site serves everything else. This typically requires a reverse proxy (nginx) or custom hosting layout.

## 2) Azure DevOps + Azure prerequisites

### Azure resources (public)
- Azure Subscription + Resource Group
- **Azure Static Web App** (frontend)
- **App Service Plan (Linux)** + **Web App (backend)**
- **Azure Front Door (Standard/Premium)**
- Optional but recommended:
  - **Key Vault** (secrets)
  - **Application Insights** (observability)

### Azure DevOps configuration
- Azure DevOps Project + Azure Repos repository
- A Service Connection with permissions to deploy (recommended: **Azure Resource Manager** service connection)

### Recommended resource names (example)
Use a consistent prefix so Front Door + App Service + SWA are easy to associate.

- Resource Group: `rg-mbse-prod` (or `rg-mbse-dev`)
- Static Web App: `swa-mbse-prod`
- App Service Plan (Linux): `asp-mbse-prod`
- App Service (backend): `app-mbse-api-prod`
- Front Door profile: `fd-mbse-prod`
- Key Vault: `kv-mbse-prod`
- Application Insights: `appi-mbse-prod`

### Azure DevOps pipeline variables (required)

**Frontend pipeline** (`AzureStaticWebApp@0`)
- `AZURE_SWA_TOKEN` (secret) – deployment token from the Static Web App
- `VITE_API_KEY` (secret, optional) – only if the backend enforces `API_KEY`

**Backend pipeline** (`AzureWebApp@1`)
- An Azure Resource Manager **service connection name** (configured in the pipeline YAML as `azureSubscription: '<YOUR_AZURE_SERVICE_CONNECTION>'`)
- Backend App Service name (configured in YAML as `appName: '<YOUR_BACKEND_APP_SERVICE_NAME>'`)

Notes:
- Prefer storing secrets in a Variable Group backed by Key Vault.
- Backend runtime secrets like `NEO4J_PASSWORD` should be App Service Application Settings (ideally Key Vault references), not pipeline variables.

## 3) Runtime configuration (environment variables)

### Backend (App Service → Configuration → Application settings)
Set these as **App Settings** (do not commit secrets to git).

**Required**
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`

**Strongly recommended for non-dev**
- `JWT_SECRET_KEY`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`

**Optional (auth hardening)**
- `API_KEY` (if set, backend expects `X-API-Key`)

**Optional**
- `LOG_LEVEL`
- `DATA_DIR`
- `OUTPUT_DIR`
- `REDIS_ENABLED` (`true`/`false`)
- `REDIS_URL`

**Optional (Azure AI baseline integration)**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT`
- `AZURE_OPENAI_API_VERSION`
- `AZURE_AI_SEARCH_ENDPOINT`
- `AZURE_AI_SEARCH_INDEX`
- `AZURE_AI_SEARCH_API_KEY`
- `AZURE_KEY_VAULT_URL`
- `APPLICATIONINSIGHTS_CONNECTION_STRING`

Notes:
- See `.env.example` for the authoritative list.
- Prefer **Key Vault references** for secrets (next section).

### Frontend (build-time variables)

The frontend uses `VITE_API_KEY` (optional) to send `X-API-Key`.

- `VITE_API_KEY` (optional)

The frontend’s API base path is **`/api`** (relative). In production, Front Door must route `/api/*` to the backend.

For local dev only, Vite dev server proxy target is controlled by:
- `API_BASE_URL` (used by `frontend/vite.config.ts`, default `http://127.0.0.1:5000`)

## 4) Secrets via Key Vault (recommended)

1. Create an Azure Key Vault.
2. Add secrets such as `NEO4J_PASSWORD`, `JWT_SECRET_KEY`, `API_KEY`, etc.
3. Grant the Web App identity access (Managed Identity recommended):
   - Key Vault access policy or RBAC role allowing `get` on secrets.
4. In App Service Application settings, reference secrets using Key Vault references, e.g.:
   - `NEO4J_PASSWORD = @Microsoft.KeyVault(SecretUri=https://<kv>.vault.azure.net/secrets/NEO4J_PASSWORD/<version>)`

## 5) Backend deployment (Azure App Service - Python)

### Backend start command

In the Web App configuration, set a startup command compatible with ASGI.

Recommended (App Service Linux):
- `gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} src.web.app_fastapi:app`

Important:
- App Service typically provides a `PORT` env var. Binding to `${PORT}` is safest.
- Ensure the deployed package’s **root** is the `backend/` folder so `src.web.app_fastapi:app` resolves.

### Build + package expectations
- Backend dependencies are in:
  - `backend/requirements.txt`
  - `backend/requirements-phase2.txt` (optional, if Phase 2 features are enabled)

## 6) Frontend deployment (Azure Static Web Apps)

### Build output
From repo root:
- `npm install`
- `npm run build`

This produces a static site under:
- `dist/`

### Hosting

Use **Azure Static Web Apps** to serve `dist/`.

Because you selected Front Door, the browser should access the app via the **Front Door endpoint hostname**, and Front Door will:
- Send `/*` traffic to SWA
- Send `/api/*` traffic to App Service

## 7) Azure Front Door configuration (minimal)

Create a Front Door profile (Standard or Premium), then configure:

1. **Origins**
- `origin-frontend` → your Static Web App default hostname
- `origin-backend` → your App Service default hostname

2. **Routes**
- `route-frontend`
  - Patterns: `/*`
  - Origin group: `origin-frontend`
- `route-backend`
  - Patterns: `/api/*`
  - Origin group: `origin-backend`

3. **HTTPS**
- Add your custom domain (optional) and enable HTTPS on Front Door.

Notes:
- With this setup, the UI and API share the same public host, so browser CORS issues are typically avoided.
- If you add caching rules, avoid caching `/api/*` unless you explicitly know which endpoints are safe.

## 8) Azure Pipelines (minimal examples)

These snippets are intended as a starting point. Customize resource names and service connections.

### 8.1 Backend: build and deploy to App Service

```yaml
# azure-pipelines-backend.yml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

variables:
  pythonVersion: '3.12'

steps:
  - checkout: self

  - task: UsePythonVersion@0
    inputs:
      versionSpec: '$(pythonVersion)'

  - script: |
      python -m pip install --upgrade pip
      pip install -r backend/requirements.txt
      if [ -f backend/requirements-phase2.txt ]; then pip install -r backend/requirements-phase2.txt; fi
    displayName: Install backend dependencies

  # Package backend directory as zip for App Service deployment
  - task: ArchiveFiles@2
    inputs:
      rootFolderOrFile: 'backend'
      includeRootFolder: false
      archiveType: 'zip'
      archiveFile: '$(Build.ArtifactStagingDirectory)/backend.zip'
      replaceExistingArchive: true

  - publish: '$(Build.ArtifactStagingDirectory)/backend.zip'
    artifact: backend

  - task: AzureWebApp@1
    inputs:
      azureSubscription: '<YOUR_AZURE_SERVICE_CONNECTION>'
      appType: 'webAppLinux'
      appName: '<YOUR_BACKEND_APP_SERVICE_NAME>'
      package: '$(Build.ArtifactStagingDirectory)/backend.zip'
```

### 8.2 Frontend: build and deploy (Static Web Apps)

```yaml
# azure-pipelines-frontend.yml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: 'ubuntu-latest'

steps:
  - checkout: self

  - task: NodeTool@0
    inputs:
      versionSpec: '20.x'

  - script: |
      npm install
      npm run build
    displayName: Build frontend
    env:
      # Optional: only needed if your backend enforces API key authentication.
      VITE_API_KEY: $(VITE_API_KEY)

  # Deploy to Azure Static Web Apps
  - task: AzureStaticWebApp@0
    inputs:
      azure_static_web_apps_api_token: '$(AZURE_SWA_TOKEN)'
      app_location: '/'
      output_location: 'dist'
```

Notes:
- Store tokens/secrets in a **Variable Group** linked to Key Vault, or as secret variables.
- For Option A, users should browse the app via the **Front Door hostname** so `/api/*` routes correctly.

## 9) Validation checklist

- Backend responds:
  - `GET /api/health`
  - `GET /api/docs`
- Frontend loads and can call backend endpoints through `/api/*`.
- Neo4j connectivity works (Aura URI/user/password configured).
- If `API_KEY` is set server-side, frontend has `VITE_API_KEY` set at build time.

## 10) Related docs

- Azure AI baseline deployment notes: `docs/azure-ai-baseline/DEPLOYMENT_REFERENCE.md`
- Repo env variables: `.env.example`
