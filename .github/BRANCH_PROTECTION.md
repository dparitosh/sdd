# Branch Protection Configuration

This document describes the branch protection rules that should be configured in GitHub repository settings.

## GitHub Repository Settings

Navigate to: **Settings → Branches → Branch protection rules**

## Protection Rule for `main` Branch

### Branch Name Pattern
```
main
```

### Settings

#### Protect matching branches
- [x] **Require a pull request before merging**
  - [x] Require approvals: **2**
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [x] Require review from Code Owners
  - [ ] Restrict who can dismiss pull request reviews (optional)
  - [x] Allow specified actors to bypass required pull requests (for emergency hotfixes)
  - [x] Require approval of the most recent reviewable push

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - **Required status checks:**
    - `git-validation`
    - `lint / Lint Python Code`
    - `test-backend / Test Backend (Python) (3.12)`
    - `test-frontend / Test Frontend (React)`
    - `build-docker / Build Docker Images`
    - `security-scan / Security Scan`

- [x] **Require conversation resolution before merging**

- [x] **Require signed commits**

- [x] **Require linear history** (squash merging or rebase merging only)

- [x] **Require deployments to succeed before merging** (if using GitHub Environments)
  - Required environments: `production`

#### Rules applied to everyone including administrators
- [x] **Restrict who can push to matching branches**
  - Allow: CI/CD service accounts only
  - Deny: All users (must use pull requests)

- [x] **Allow force pushes**
  - [ ] Everyone (disabled)
  - [ ] Specify who can force push (disabled)

- [x] **Allow deletions**
  - [ ] Disabled (cannot delete main branch)

### Additional Settings

#### Lock branch
- [ ] Disabled (branch is not read-only)

#### Do not allow bypassing the above settings
- [x] Enabled (administrators must follow rules)

---

## Protection Rule for `develop` Branch

### Branch Name Pattern
```
develop
```

### Settings

#### Protect matching branches
- [x] **Require a pull request before merging**
  - [x] Require approvals: **1**
  - [x] Dismiss stale pull request approvals when new commits are pushed
  - [ ] Require review from Code Owners (optional)

- [x] **Require status checks to pass before merging**
  - [x] Require branches to be up to date before merging
  - **Required status checks:**
    - `git-validation`
    - `lint / Lint Python Code`
    - `test-backend / Test Backend (Python) (3.12)`
    - `test-frontend / Test Frontend (React)`

- [x] **Require conversation resolution before merging**

- [ ] Require signed commits (optional for develop)

- [ ] Require linear history (optional)

#### Rules applied to everyone including administrators
- [x] **Restrict who can push to matching branches**
  - Allow: Core team members + CI/CD
  - Deny: External contributors (must use pull requests)

- [x] **Allow force pushes**
  - [x] Specify who can force push
    - Team: Core Developers (use with extreme caution)

- [x] **Allow deletions**
  - [ ] Disabled (cannot delete develop branch)

---

## Protection Rules for Feature/Bugfix/Hotfix Branches

### Branch Name Pattern
```
feature/*
bugfix/*
hotfix/*
release/*
```

### Settings (Lightweight Protection)

#### Protect matching branches
- [ ] **Require a pull request before merging** (disabled - PRs created manually)

- [x] **Require status checks to pass before merging**
  - **Required status checks:**
    - `lint / Lint Python Code`
    - `test-backend / Test Backend (Python) (3.12)`

- [ ] **Allow force pushes**
  - [x] Everyone (developers can rebase their feature branches)

- [ ] **Allow deletions**
  - [x] Everyone (can delete after merging)

---

## Rulesets (Alternative to Branch Protection)

GitHub Rulesets provide more flexible protection. Configure at: **Settings → Rules → Rulesets**

### Ruleset: Production Protection

**Target branches:** `main`

**Rules:**
1. **Require pull request**
   - Require approvals: 2
   - Dismiss stale reviews: Yes
   - Require code owner review: Yes

2. **Require status checks**
   - Require all status checks to pass
   - Block merge if checks are running

3. **Require deployments to succeed**
   - Environments: `production`

4. **Block force pushes**

5. **Restrict deletions**

6. **Require signed commits**

### Ruleset: Development Protection

**Target branches:** `develop`

**Rules:**
1. **Require pull request**
   - Require approvals: 1

2. **Require status checks**
   - Core checks must pass

3. **Allow force pushes** (with restrictions)

---

## CODEOWNERS File

Create `.github/CODEOWNERS` to define code ownership:

```
# Default owners for everything
* @dparitosh

# Backend code
/src/ @backend-team
/tests/ @backend-team

# Frontend code
/frontend/ @frontend-team

# Infrastructure
/deployment/ @devops-team
/docker/ @devops-team
/.github/ @devops-team

# MCP Server
/mcp-server/ @mcp-team

# Documentation
/docs/ @dparitosh @documentation-team
*.md @documentation-team

# PLM Connectors (requires domain expert review)
/src/integrations/teamcenter_connector.py @plm-team @senior-engineers
/src/integrations/windchill_connector.py @plm-team @senior-engineers
/src/integrations/sap_odata_connector.py @plm-team @senior-engineers

# Security-sensitive files
/src/web/middleware/auth.py @security-team
/src/web/middleware/rbac.py @security-team
SECURITY.md @security-team

# Agent framework (critical components)
/src/agents/ @ai-team @senior-engineers

# Database schema changes
/scripts/*migration* @database-team @senior-engineers
```

---

## Status Checks Configuration

Required status checks that must pass before merging:

### For `main` branch:
1. ✅ `git-validation` - Branch naming, commit messages, conflicts
2. ✅ `lint / Lint Python Code` - Black, Flake8, mypy
3. ✅ `test-backend / Test Backend (Python) (3.12)` - pytest with Neo4j
4. ✅ `test-frontend / Test Frontend (React)` - TypeScript, build
5. ✅ `build-docker / Build Docker Images` - Docker image builds
6. ✅ `security-scan / Security Scan` - Trivy vulnerability scan

### For `develop` branch:
1. ✅ `git-validation`
2. ✅ `lint / Lint Python Code`
3. ✅ `test-backend / Test Backend (Python) (3.12)`
4. ✅ `test-frontend / Test Frontend (React)`

---

## Auto-merge Configuration

Enable auto-merge for dependabot PRs:

1. Navigate to: **Settings → Code security and analysis**
2. Enable: **Dependabot alerts**
3. Enable: **Dependabot security updates**
4. Configure auto-merge rules in `.github/workflows/auto-merge-dependabot.yml`

---

## Merge Strategies

Configure allowed merge methods: **Settings → General → Pull Requests**

### Recommended Configuration
- [x] **Allow squash merging** (default for feature branches)
  - Default commit message: Pull request title
  - Default commit description: Pull request description
  
- [ ] **Allow merge commits** (disabled for clean history)
  
- [x] **Allow rebase merging** (for maintaining linear history)

- [x] **Automatically delete head branches** (cleanup after merge)

---

## Deployment Environments

Configure at: **Settings → Environments**

### Environment: `production`
- **Protection rules:**
  - Required reviewers: 2 (senior engineers)
  - Wait timer: 0 minutes (or 30 minutes for safety)
  - Deployment branches: `main` only
  
- **Environment secrets:**
  - `NEO4J_URI`
  - `NEO4J_PASSWORD`
  - `JWT_SECRET_KEY`
  - `DEPLOY_HOST`
  - `DEPLOY_SSH_KEY`

### Environment: `staging`
- **Protection rules:**
  - Required reviewers: 1
  - Deployment branches: `develop` only
  
- **Environment secrets:**
  - `NEO4J_URI_STAGING`
  - `NEO4J_PASSWORD_STAGING`

---

## Repository Settings Checklist

- [x] Branch protection for `main` configured
- [x] Branch protection for `develop` configured
- [x] CODEOWNERS file created
- [x] Required status checks defined
- [x] Auto-delete head branches enabled
- [x] Squash merging enabled
- [x] Merge commits disabled
- [x] Rebase merging enabled
- [x] Dependabot enabled
- [x] Security alerts enabled
- [x] Production environment configured
- [x] Staging environment configured
- [x] Signed commits encouraged (optional enforcement)

---

## Implementation Steps

1. **Create CODEOWNERS file**
   ```bash
   nano .github/CODEOWNERS
   # Add ownership rules
   git add .github/CODEOWNERS
   git commit -m "chore: add CODEOWNERS file"
   ```

2. **Configure branch protection in GitHub UI**
   - Go to repository Settings
   - Navigate to Branches
   - Add rules as documented above

3. **Set up environments**
   - Go to Settings → Environments
   - Create `production` and `staging`
   - Add protection rules and secrets

4. **Enable security features**
   - Enable Dependabot alerts
   - Enable secret scanning
   - Enable code scanning (CodeQL)

5. **Test protection rules**
   - Try to push directly to `main` (should fail)
   - Create a PR without required checks (should block merge)
   - Test with a test PR

---

## Monitoring and Maintenance

### Weekly Tasks
- Review open pull requests
- Check for stale branches
- Monitor failed CI/CD runs
- Review Dependabot PRs

### Monthly Tasks
- Review branch protection effectiveness
- Update CODEOWNERS if team changes
- Audit user permissions
- Review deployment logs

### Quarterly Tasks
- Review and update branch strategy
- Evaluate CI/CD pipeline performance
- Update documentation
- Team training on Git workflow
