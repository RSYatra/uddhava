# Development Workflow & Quality Controls

This document explains the complete quality control system for this project.

## Overview

We use a **layered approach** to ensure code quality:

```
1. Pre-commit hooks (local, instant feedback)
   ↓
2. CI pipeline (GitHub Actions, comprehensive validation)
   ↓
3. Branch protection (enforced review & checks)
   ↓
4. Automatic deployment (to production)
```

## Layer 1: Pre-commit Hooks

**When**: Before every `git commit`
**Speed**: <5 seconds
**Purpose**: Catch simple issues instantly

### What Runs

1. **Ruff** - Format & lint code
2. **mypy** - Type checking
3. **Bandit** - Security analysis
4. **File checks** - Whitespace, YAML, large files
5. **Custom security** - Hardcoded credentials scan
6. **Import validation** - Python imports work

### Setup

```bash
pip install pre-commit
pre-commit install
```

### Manual Run

```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update hooks
pre-commit autoupdate
```

### Skip (Emergency Only)

```bash
git commit --no-verify -m "emergency fix"
```

## Layer 2: CI Pipeline

**When**: On every push & pull request
**Speed**: 3-5 minutes
**Purpose**: Comprehensive validation

### Jobs & What They Check

#### 1. Code Quality (2-3 min)
- **Formatting**: Ruff format check
- **Linting**: Ruff rules (500+ checks)
- **Type Safety**: mypy static analysis

#### 2. Security (2-3 min)
- **TruffleHog**: Secret scanning
- **Credential scan**: Hardcoded passwords/keys
- **Bandit**: Python security issues
- **pip-audit**: Dependency vulnerabilities

#### 3. Tests & Coverage (1-2 min)
- **pytest**: All unit/integration tests
- **Coverage**: Code coverage report
- **Codecov**: Upload coverage metrics

#### 4. Build Validation (1 min)
- **Import test**: All modules importable
- **Config check**: No hardcoded values
- **Startup test**: Application starts

#### 5. Migration Validation (30 sec)
- **Alembic config**: Valid configuration
- **Conflict detection**: Duplicate revisions
- **Syntax check**: Migrations are valid

#### 6. PR Quality (pull requests only)
- **Size check**: Warn if >500 lines
- **File check**: No .env files

### Configuration Files

- **CI Workflow**: `.github/workflows/ci.yml`
- **Ruff**: `ruff.toml`
- **mypy**: `pyproject.toml`
- **pytest**: `pyproject.toml`
- **Bandit**: `pyproject.toml`

## Layer 3: Branch Protection

**When**: Before merge to `main`
**Purpose**: Enforce quality gates

### Requirements

- ✓ All CI checks must pass
- ✓ At least 1 code review approval
- ✓ All conversations resolved
- ✓ Branch up to date with `main`
- ✓ Code owners review (if applicable)

### What's Blocked

- Direct push to `main`
- Merge without approval
- Merge with failing tests
- Merge with security issues
- Merge with unresolved comments

## Development Workflow

### 1. Start New Work

```bash
git checkout main
git pull origin main
git checkout -b feature/your-feature-name
```

### 2. Write Code

```bash
# Make changes
# Pre-commit hooks run automatically on commit
git add .
git commit -m "feat: your changes"
```

### 3. Push & Create PR

```bash
git push origin feature/your-feature-name
# Go to GitHub and create Pull Request
```

### 4. CI Runs Automatically

Watch the checks run on your PR. Fix any failures:

```bash
# Make fixes
git add .
git commit -m "fix: address CI feedback"
git push origin feature/your-feature-name
```

### 5. Code Review

- Request review from team
- Address feedback
- Resolve all conversations

### 6. Merge

- Once approved and all checks pass
- Merge the PR
- Automatic deployment to production

### 7. Cleanup

```bash
git checkout main
git pull origin main
git branch -d feature/your-feature-name
```

## Configuration Standards

### Ruff (Linting & Formatting)

- **Line length**: 100 characters
- **Quote style**: Double quotes
- **Rules**: 500+ checks enabled
- **Config**: `ruff.toml`

### mypy (Type Checking)

- **Python version**: 3.11
- **Strict**: No (gradually adopting)
- **Ignore missing imports**: Yes
- **Config**: `pyproject.toml`

### pytest (Testing)

- **Test discovery**: `tests/test_*.py`
- **Coverage minimum**: Not enforced (tracked)
- **Config**: `pyproject.toml`

### Bandit (Security)

- **Severity**: Low and above
- **Skip**: B101 (assert in tests)
- **Config**: `pyproject.toml`

## Common Issues & Solutions

### Pre-commit Hook Fails

```bash
# See what failed
git status

# Fix issues
ruff format .
ruff check . --fix

# Try commit again
git commit -m "your message"
```

### CI Fails

1. **Check the logs** in GitHub Actions
2. **Run locally** to reproduce
3. **Fix the issue**
4. **Push the fix**

### Type Errors

```bash
# Run mypy locally
mypy . --config-file=pyproject.toml

# Common fixes:
# - Add type hints
# - Use # type: ignore for third-party libs
# - Update pyproject.toml to exclude file
```

### Security Alerts

```bash
# For hardcoded credentials
# - Move to environment variables
# - Use .env files (not committed)

# For dependency vulnerabilities
# - Update the package
# - Check if it's a dev-only dependency
```

### Test Failures

```bash
# Run tests locally
pytest

# Run specific test
pytest tests/test_authentication.py::test_login

# Run with verbose output
pytest -v --tb=short
```

## Emergency Procedures

### Skip Pre-commit (Not Recommended)

```bash
git commit --no-verify -m "emergency fix"
```

### Force Push (After Branch Protection)

1. Temporarily disable branch protection
2. Make the fix
3. Re-enable branch protection
4. Create a follow-up PR to fix properly

### Hotfix Process

```bash
git checkout -b hotfix/critical-issue main
# Make minimal fix
git push origin hotfix/critical-issue
# Create PR with [HOTFIX] prefix
# Self-approve if necessary
# Merge and deploy
# Create follow-up PR for proper fix
```

## Best Practices

### Commit Messages

Use conventional commits:

```
feat: add new feature
fix: bug fix
docs: documentation
style: formatting
refactor: code restructuring
test: add tests
chore: maintenance
```

### PR Size

- Keep PRs under 500 lines when possible
- Break large features into smaller PRs
- Makes review faster and easier

### Testing

- Write tests for new features
- Update tests for bug fixes
- Aim for >70% coverage on new code

### Security

- Never commit secrets
- Use environment variables
- Review security scan results

### Code Review

- Review your own PR first
- Respond to feedback promptly
- Explain complex changes
- Be respectful and constructive

## Continuous Improvement

This system evolves. Suggestions welcome:

1. Create an issue with `enhancement` label
2. Discuss in team meetings
3. Update this documentation
4. Update configuration files

## Questions?

- Check this documentation
- Review existing PRs
- Ask in team chat
- Create a discussion issue

---

Last updated: November 2024
