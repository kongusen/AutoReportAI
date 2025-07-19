# CI/CD Pipeline Documentation

This document describes the Continuous Integration and Continuous Deployment (CI/CD) pipeline for AutoReportAI.

## Pipeline Overview

Our CI/CD strategy uses GitHub Actions with multiple workflows designed for efficiency, reliability, and comprehensive quality assurance.

### Workflow Architecture

```mermaid
graph TD
    A[Code Push/PR] --> B{Trigger Event}
    B --> C[Quality Gate]
    B --> D[Unit Tests]
    B --> E[Integration Tests]
    
    C --> F[Linting]
    C --> G[Type Checking]
    C --> H[Security Scan]
    
    D --> I[Fast Unit Tests]
    D --> J[Coverage Report]
    
    E --> K[Database Tests]
    E --> L[API Tests]
    E --> M[E2E Tests]
    
    F --> N{All Checks Pass?}
    G --> N
    H --> N
    I --> N
    J --> N
    K --> N
    L --> N
    M --> N
    
    N -->|Yes| O[Deploy to Staging]
    N -->|No| P[Block Merge]
    
    O --> Q[Production Deploy]
```

## Workflow Files

### 1. Quality Gate Workflow (`.github/workflows/quality.yml`)

**Purpose**: Fast code quality checks that run on every push and PR
**Duration**: ~2-3 minutes
**Triggers**: `push`, `pull_request`

**Jobs**:
- **Linting**: flake8 code style checks
- **Formatting**: Black code formatting verification
- **Import Sorting**: isort import organization checks
- **Type Checking**: mypy static type analysis (if configured)
- **Security Scanning**: bandit security vulnerability detection

**Configuration**:
```yaml
name: Quality Gate
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  quality-checks:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11]
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements/*.txt') }}
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements/development.txt
    
    - name: Run linting
      run: |
        cd backend
        flake8 app/ --count --select=E9,F63,F7,F82 --show-source --statistics
        flake8 app/ --count --exit-zero --max-complexity=10 --max-line-length=88 --statistics
    
    - name: Check code formatting
      run: |
        cd backend
        black --check app/ tests/
    
    - name: Check import sorting
      run: |
        cd backend
        isort --check-only app/ tests/
    
    - name: Security scan
      run: |
        cd backend
        bandit -r app/ -f json -o bandit-report.json || true
        bandit -r app/ --severity-level medium
```

### 2. Unit Tests Workflow (`.github/workflows/unit-tests.yml`)

**Purpose**: Fast unit tests with code coverage
**Duration**: ~1-2 minutes
**Triggers**: `push`, `pull_request`

**Features**:
- Parallel execution across Python versions
- Code coverage reporting
- Coverage enforcement (>80%)
- Artifact upload for coverage reports

**Key Configuration**:
```yaml
name: Unit Tests
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ matrix.python-version }}-${{ hashFiles('**/requirements/*.txt') }}
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements/testing.txt
    
    - name: Run unit tests
      run: |
        cd backend
        pytest tests/unit/ -v -m "not slow" --cov=app --cov-report=xml --cov-report=html
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./backend/coverage.xml
        flags: unittests
        name: codecov-umbrella
    
    - name: Upload coverage artifacts
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report-${{ matrix.python-version }}
        path: backend/htmlcov/
```

### 3. Integration Tests Workflow (`.github/workflows/integration-tests.yml`)

**Purpose**: Integration tests with database and external services
**Duration**: ~5-8 minutes
**Triggers**: `push` to main, `pull_request`

**Features**:
- PostgreSQL service container
- Database migration testing
- API endpoint testing
- Service integration testing

**Key Configuration**:
```yaml
name: Integration Tests
on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  integration-tests:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: test_password
          POSTGRES_USER: test_user
          POSTGRES_DB: test_db
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
    
    steps:
    - uses: actions/checkout@v4
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: 3.11
    
    - name: Install dependencies
      run: |
        cd backend
        pip install -r requirements/testing.txt
    
    - name: Run database migrations
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
      run: |
        cd backend
        alembic upgrade head
    
    - name: Run integration tests
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
      run: |
        cd backend
        pytest tests/integration/ -v --cov=app --cov-append
    
    - name: Run E2E tests
      env:
        DATABASE_URL: postgresql://test_user:test_password@localhost:5432/test_db
      run: |
        cd backend
        pytest tests/e2e/ -v --cov=app --cov-append
```

### 4. Main CI/CD Workflow (`.github/workflows/ci-cd.yml`)

**Purpose**: Comprehensive pipeline for main branch deployments
**Duration**: ~10-15 minutes
**Triggers**: `push` to main, releases

**Features**:
- Multi-stage pipeline (test → build → deploy)
- Docker image building
- Deployment to staging/production
- Rollback capabilities

## Pipeline Stages

### Stage 1: Quality Gate (Parallel)

**Duration**: ~2-3 minutes
**Runs on**: Every push and PR

```bash
# Code Quality Checks
- Linting (flake8)
- Code formatting (black)
- Import sorting (isort)
- Security scanning (bandit)
- Type checking (mypy)
```

**Success Criteria**: All quality checks must pass

### Stage 2: Unit Tests (Parallel)

**Duration**: ~1-2 minutes
**Runs on**: Every push and PR

```bash
# Fast Unit Tests
- Individual component tests
- Business logic validation
- Mock-based testing
- Code coverage > 80%
```

**Success Criteria**: All tests pass, coverage threshold met

### Stage 3: Integration Tests

**Duration**: ~5-8 minutes
**Runs on**: Main branch, PRs to main

```bash
# Integration Testing
- Database integration tests
- API endpoint tests
- Service interaction tests
- End-to-end workflow tests
```

**Success Criteria**: All integration tests pass

### Stage 4: Build & Deploy (Production Only)

**Duration**: ~3-5 minutes
**Runs on**: Main branch pushes, releases

```bash
# Build Process
- Docker image creation
- Dependency optimization
- Security scanning
- Image tagging and push
```

## Environment Configuration

### Development Environment

**Triggers**: Feature branch pushes
**Database**: Ephemeral PostgreSQL container
**External Services**: Mocked
**Deployment**: None

### Staging Environment

**Triggers**: Pull requests to main
**Database**: Staging PostgreSQL instance
**External Services**: Staging/sandbox APIs
**Deployment**: Automatic to staging environment

### Production Environment

**Triggers**: Main branch pushes, releases
**Database**: Production PostgreSQL instance
**External Services**: Production APIs
**Deployment**: Manual approval required

## Secrets and Environment Variables

### Required Secrets

Configure these secrets in GitHub repository settings:

```bash
# Database
DATABASE_URL                 # Production database connection
STAGING_DATABASE_URL        # Staging database connection

# Security
SECRET_KEY                  # JWT signing key
ENCRYPTION_KEY             # Data encryption key

# External Services
OPENAI_API_KEY             # OpenAI API access
SMTP_PASSWORD              # Email service password

# Deployment
DOCKER_REGISTRY_URL        # Container registry
DOCKER_REGISTRY_USERNAME   # Registry authentication
DOCKER_REGISTRY_PASSWORD   # Registry authentication

# Monitoring
SENTRY_DSN                 # Error tracking
CODECOV_TOKEN              # Code coverage reporting
```

### Environment Variables

```yaml
# .github/workflows/ci-cd.yml
env:
  PYTHON_VERSION: 3.11
  NODE_VERSION: 18
  POSTGRES_VERSION: 15
  COVERAGE_THRESHOLD: 80
  DOCKER_BUILDKIT: 1
```

## Caching Strategy

### Dependency Caching

```yaml
- name: Cache Python dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements/*.txt') }}
    restore-keys: |
      ${{ runner.os }}-pip-

- name: Cache Node dependencies
  uses: actions/cache@v3
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
    restore-keys: |
      ${{ runner.os }}-node-
```

### Docker Layer Caching

```yaml
- name: Set up Docker Buildx
  uses: docker/setup-buildx-action@v2
  with:
    driver-opts: image=moby/buildkit:master

- name: Build and push Docker image
  uses: docker/build-push-action@v4
  with:
    context: .
    push: true
    tags: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    cache-from: type=gha
    cache-to: type=gha,mode=max
```

## Monitoring and Notifications

### Status Badges

Add these badges to your README:

```markdown
[![CI/CD Pipeline](https://github.com/username/AutoReportAI/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/username/AutoReportAI/actions/workflows/ci-cd.yml)
[![Quality Gate](https://github.com/username/AutoReportAI/actions/workflows/quality.yml/badge.svg)](https://github.com/username/AutoReportAI/actions/workflows/quality.yml)
[![Unit Tests](https://github.com/username/AutoReportAI/actions/workflows/unit-tests.yml/badge.svg)](https://github.com/username/AutoReportAI/actions/workflows/unit-tests.yml)
[![Integration Tests](https://github.com/username/AutoReportAI/actions/workflows/integration-tests.yml/badge.svg)](https://github.com/username/AutoReportAI/actions/workflows/integration-tests.yml)
[![codecov](https://codecov.io/gh/username/AutoReportAI/branch/main/graph/badge.svg)](https://codecov.io/gh/username/AutoReportAI)
```

### Slack Notifications

```yaml
- name: Notify Slack on failure
  if: failure()
  uses: 8398a7/action-slack@v3
  with:
    status: failure
    channel: '#ci-cd'
    webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### Email Notifications

```yaml
- name: Send email notification
  if: failure() && github.ref == 'refs/heads/main'
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 587
    username: ${{ secrets.EMAIL_USERNAME }}
    password: ${{ secrets.EMAIL_PASSWORD }}
    subject: "CI/CD Pipeline Failed - ${{ github.repository }}"
    body: "Pipeline failed for commit ${{ github.sha }}"
    to: team@company.com
```

## Performance Optimization

### Parallel Execution

```yaml
strategy:
  matrix:
    python-version: [3.11, 3.12]
    test-group: [unit, integration, e2e]
  fail-fast: false
  max-parallel: 6
```

### Conditional Execution

```yaml
- name: Run expensive tests
  if: github.event_name == 'push' && github.ref == 'refs/heads/main'
  run: pytest tests/e2e/ -v

- name: Skip tests on docs changes
  if: "!contains(github.event.head_commit.message, '[skip ci]')"
  run: pytest tests/
```

### Resource Optimization

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    container:
      image: python:3.11-slim
      options: --cpus 2 --memory 4g
```

## Troubleshooting

### Common Issues

1. **Test Failures**:
   ```bash
   # Check test logs in GitHub Actions
   # Run tests locally to reproduce
   cd backend
   make test-unit
   make test-integration
   ```

2. **Database Connection Issues**:
   ```yaml
   # Ensure service health checks
   services:
     postgres:
       options: >-
         --health-cmd pg_isready
         --health-interval 10s
         --health-timeout 5s
         --health-retries 5
   ```

3. **Cache Issues**:
   ```bash
   # Clear cache in GitHub Actions
   # Update cache keys when dependencies change
   ```

4. **Secret Configuration**:
   ```bash
   # Verify secrets are set in repository settings
   # Check secret names match workflow references
   ```

### Debugging Workflows

1. **Enable Debug Logging**:
   ```yaml
   - name: Debug step
     run: echo "Debug info: ${{ toJson(github) }}"
     env:
       ACTIONS_STEP_DEBUG: true
   ```

2. **SSH into Runner** (for debugging):
   ```yaml
   - name: Setup tmate session
     if: failure()
     uses: mxschmitt/action-tmate@v3
   ```

3. **Artifact Collection**:
   ```yaml
   - name: Upload logs
     if: always()
     uses: actions/upload-artifact@v3
     with:
       name: test-logs
       path: |
         backend/logs/
         backend/htmlcov/
   ```

## Security Considerations

### Secret Management

- Use GitHub Secrets for sensitive data
- Rotate secrets regularly
- Use environment-specific secrets
- Never log secret values

### Container Security

```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
    format: 'sarif'
    output: 'trivy-results.sarif'

- name: Upload Trivy scan results
  uses: github/codeql-action/upload-sarif@v2
  with:
    sarif_file: 'trivy-results.sarif'
```

### Code Security

```yaml
- name: Run CodeQL Analysis
  uses: github/codeql-action/analyze@v2
  with:
    languages: python
```

## Best Practices

### Workflow Design

1. **Fail Fast**: Run quick checks first
2. **Parallel Execution**: Run independent jobs in parallel
3. **Conditional Logic**: Skip unnecessary steps
4. **Resource Efficiency**: Use appropriate runner sizes
5. **Clear Naming**: Use descriptive job and step names

### Testing Strategy

1. **Test Pyramid**: More unit tests, fewer E2E tests
2. **Test Isolation**: Each test should be independent
3. **Data Management**: Use fixtures and factories
4. **Performance**: Keep tests fast and reliable

### Deployment Strategy

1. **Blue-Green Deployment**: Zero-downtime deployments
2. **Rollback Plan**: Quick rollback capabilities
3. **Health Checks**: Verify deployment success
4. **Monitoring**: Track deployment metrics

## Maintenance

### Regular Tasks

1. **Update Dependencies**: Keep actions and dependencies current
2. **Review Metrics**: Monitor pipeline performance
3. **Clean Artifacts**: Remove old build artifacts
4. **Update Documentation**: Keep CI/CD docs current

### Performance Monitoring

```yaml
- name: Report pipeline metrics
  run: |
    echo "Pipeline duration: ${{ steps.pipeline-start.outputs.time }}"
    echo "Test count: $(pytest --collect-only -q | grep test | wc -l)"
    echo "Coverage: $(coverage report --show-missing | grep TOTAL | awk '{print $4}')"
```

For more information about specific workflows or troubleshooting, check the individual workflow files in `.github/workflows/`.