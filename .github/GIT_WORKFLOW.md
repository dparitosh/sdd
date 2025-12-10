# Git Branching Strategy

## Branch Structure

```
main (production)
  │
  ├─ develop (integration)
  │   │
  │   ├─ feature/user-authentication
  │   ├─ feature/plm-integration
  │   └─ feature/simulation-workflow
  │
  ├─ release/v1.0.0 (release preparation)
  │
  ├─ hotfix/critical-security-patch (production fixes)
  │
  └─ bugfix/fix-neo4j-connection (bug fixes)
```

## Branch Types

### 1. Main Branch (`main`)
- **Purpose**: Production-ready code
- **Protection**: 
  - Require pull request reviews (2 approvers)
  - Require status checks to pass
  - Require branches to be up to date
  - No direct commits
- **Deployment**: Auto-deploys to production on merge
- **Naming**: `main`

### 2. Develop Branch (`develop`)
- **Purpose**: Integration branch for features
- **Protection**:
  - Require pull request reviews (1 approver)
  - Require status checks to pass
- **Deployment**: Auto-deploys to staging on merge
- **Naming**: `develop`

### 3. Feature Branches
- **Purpose**: New features and enhancements
- **Created from**: `develop`
- **Merged into**: `develop`
- **Naming**: `feature/<short-description>`
  - ✅ `feature/plm-teamcenter-sync`
  - ✅ `feature/multi-agent-orchestration`
  - ❌ `new-feature` (missing prefix)
  - ❌ `feature` (no description)

### 4. Bugfix Branches
- **Purpose**: Non-critical bug fixes
- **Created from**: `develop`
- **Merged into**: `develop`
- **Naming**: `bugfix/<short-description>`
  - ✅ `bugfix/fix-neo4j-timeout`
  - ✅ `bugfix/authentication-error`

### 5. Hotfix Branches
- **Purpose**: Critical production fixes
- **Created from**: `main`
- **Merged into**: `main` AND `develop`
- **Naming**: `hotfix/<short-description>`
  - ✅ `hotfix/security-vulnerability`
  - ✅ `hotfix/data-loss-prevention`

### 6. Release Branches
- **Purpose**: Release preparation and testing
- **Created from**: `develop`
- **Merged into**: `main` AND `develop`
- **Naming**: `release/v<major>.<minor>.<patch>`
  - ✅ `release/v1.0.0`
  - ✅ `release/v2.1.3`

## Workflow Examples

### Creating a New Feature

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create feature branch
git checkout -b feature/plm-teamcenter-sync

# Make changes, commit using conventional commits
git add .
git commit -m "feat(plm): add Teamcenter BOM synchronization"

# Push to remote
git push -u origin feature/plm-teamcenter-sync

# Create pull request to develop
```

### Fixing a Production Bug (Hotfix)

```bash
# Start from main
git checkout main
git pull origin main

# Create hotfix branch
git checkout -b hotfix/security-vulnerability

# Make changes
git add .
git commit -m "fix(security): patch JWT token validation"

# Push to remote
git push -u origin hotfix/security-vulnerability

# Create PR to main (will auto-merge to develop after)
```

### Preparing a Release

```bash
# Start from develop
git checkout develop
git pull origin develop

# Create release branch
git checkout -b release/v1.0.0

# Update version numbers, CHANGELOG.md
git add .
git commit -m "chore(release): prepare v1.0.0"

# Push to remote
git push -u origin release/v1.0.0

# Create PR to main
# After merge, tag the release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `perf`: Performance improvements
- `ci`: CI/CD changes
- `build`: Build system changes
- `revert`: Reverting previous changes

### Scopes (Optional)
- `plm`: PLM integration
- `simulation`: Simulation components
- `agent`: Agent framework
- `api`: REST API
- `ui`: Frontend UI
- `mcp`: MCP server
- `auth`: Authentication
- `db`: Database

### Examples

```bash
# Feature
git commit -m "feat(plm): add SAP OData connector"

# Bug fix
git commit -m "fix(api): resolve Neo4j connection timeout"

# Documentation
git commit -m "docs: update API authentication guide"

# Breaking change
git commit -m "feat(api)!: change authentication to OAuth2

BREAKING CHANGE: JWT authentication replaced with OAuth2"
```

## Pull Request Guidelines

### Title Format
Use conventional commit format:
```
feat(scope): add new feature
fix(scope): resolve bug
```

### Description Requirements
- Clear description of changes (minimum 50 characters)
- Link related issues (`Closes #123`)
- List of changes made
- Testing performed
- Screenshots (if UI changes)

### Review Process
1. **Self-review**: Review your own code before requesting review
2. **Automated checks**: Ensure all CI/CD checks pass
3. **Peer review**: Get approval from required reviewers
4. **Address feedback**: Respond to all review comments
5. **Squash and merge**: Keep commit history clean

## Branch Protection Rules

### Main Branch
- ✅ Require pull request reviews (2 approvers)
- ✅ Require status checks (lint, test, build)
- ✅ Require conversation resolution
- ✅ Require linear history
- ✅ Do not allow bypassing
- ✅ Restrict force pushes
- ✅ Restrict deletions

### Develop Branch
- ✅ Require pull request reviews (1 approver)
- ✅ Require status checks
- ✅ Allow force pushes (with caution)
- ✅ Restrict deletions

## Release Process

### 1. Version Numbering
Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### 2. Release Checklist
- [ ] Create release branch from `develop`
- [ ] Update version in `package.json`, `setup.py`
- [ ] Update `CHANGELOG.md`
- [ ] Run full test suite
- [ ] Create PR to `main`
- [ ] Get required approvals
- [ ] Merge to `main`
- [ ] Tag release (`git tag v1.0.0`)
- [ ] Create GitHub release
- [ ] Merge `main` back to `develop`

## Git Hooks

### Pre-commit
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run linting
black --check src/ tests/
flake8 src/ tests/

# Run type checking
mypy src/
```

### Commit-msg
```bash
#!/bin/bash
# .git/hooks/commit-msg

# Validate commit message format
commit_regex='^(feat|fix|docs|style|refactor|test|chore|perf|ci|build|revert)(\(.+\))?: .{1,50}'
if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ Invalid commit message format"
    echo "Use: type(scope): description"
    exit 1
fi
```

## Troubleshooting

### Merge Conflicts
```bash
# Update your branch with latest develop
git checkout develop
git pull origin develop
git checkout feature/your-feature
git merge develop

# Resolve conflicts, then:
git add .
git commit -m "chore: resolve merge conflicts"
git push
```

### Rebase Instead of Merge
```bash
# For cleaner history
git checkout feature/your-feature
git rebase develop

# Force push (use with caution)
git push --force-with-lease
```

### Undo Last Commit
```bash
# Keep changes
git reset --soft HEAD~1

# Discard changes
git reset --hard HEAD~1
```

## Best Practices

1. **Commit Often**: Small, atomic commits are better than large ones
2. **Write Clear Messages**: Follow conventional commit format
3. **Keep PRs Small**: Easier to review and less likely to have conflicts
4. **Update Regularly**: Pull from `develop` frequently
5. **Test Before Pushing**: Run tests locally before pushing
6. **Review Your Own Code**: Self-review before requesting peer review
7. **Respond to Feedback**: Address all review comments promptly
8. **Keep History Clean**: Squash commits when merging
9. **Tag Releases**: Always tag releases with version numbers
10. **Document Breaking Changes**: Clearly document any breaking changes
