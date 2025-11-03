# Testflinger AI Coding Agent Instructions

## Project Overview
Testflinger is a system for orchestrating time-shared access to a pool of target devices for testing. It consists of a **monorepo** with 5 independent Python subprojects:
- **server/**: Flask API/web service for job queuing and management
- **agent/**: Per-device agents that request and process jobs from queues
- **device-connectors/**: Pluggable provisioning handlers for different device types (MAAS, Zapper, OEM scripts, etc.)
- **cli/**: Command-line tool for job submission and monitoring
- **common/**: Shared enums, schemas, and utilities used across all components

## Architecture & Data Flow
1. **Job Lifecycle**: Jobs move through phases defined in `common/src/testflinger_common/enums.py`:
   - `JobState`: waiting → setup → provision → firmware_update → test → cleanup → completed
   - `TestPhase`: Each phase executes via device connector commands
   - Exit code 46 from device connectors signals unrecoverable device failure

2. **Component Communication**:
   - Server exposes REST API at `/v1` endpoints (see `server/API.md`)
   - Agent polls server's queue endpoints using `testflinger_agent/client.py`
   - Agent invokes device connectors as subprocesses (not direct imports)
   - Device connectors implement `DeviceConnector` class inheriting from `DefaultDevice` in `device-connectors/src/testflinger_device_connectors/devices/__init__.py`

3. **Key Integration Points**:
   - **ProvisioningError** and **RecoveryError** in device connectors signal different failure modes
   - Agents track state via `AgentState` enum (waiting, offline, maintenance, restart)
   - Server uses MongoDB for persistence, configured in `testflinger/database.py`
   - Authentication uses OIDC (see `server/src/testflinger/oidc/`)

## Development Workflow

### Environment Setup (Per Subproject)
```bash
# Install uv package manager
sudo snap install --classic astral-uv

# In any subproject directory (agent/, cli/, etc.):
uv sync                      # Create venv and install dependencies
source .venv/bin/activate    # Activate environment
```

### Testing & Quality Checks
```bash
# Run ALL checks before committing (from subproject root):
uvx --with tox-uv tox

# Individual tox environments (see tox.ini in each subproject):
uvx --with tox-uv tox -e lock    # Verify uv.lock matches pyproject.toml
uvx --with tox-uv tox -e format  # Check ruff formatting
uvx --with tox-uv tox -e lint    # Check ruff linting
uvx --with tox-uv tox -e unit    # Run pytest with coverage
```

### Dependency Management
```bash
# Add dependency (auto-updates pyproject.toml AND uv.lock):
uv add <package>          # Production dependency
uv add --dev <package>    # Development dependency

# Remove dependency:
uv remove <package>

# Sync lock file after manual pyproject.toml edits:
uv lock
```

### Local Development Environment
For **server** development with full stack (MongoDB + Vault):
```bash
cd server/
docker-compose up -d --build   # Start on port 5000
docker exec -it testflinger-server client_credentials_admin  # Manage auth
devel/create_sample_data.py    # Add test data
```

## Project-Specific Conventions

### Code Standards
- **Line length**: 79 characters (enforced by ruff, see `pyproject.toml` files)
- **Python version**: ≥3.10 across all subprojects
- **Import style**: Device connectors are dynamically loaded by string name from `DEVICE_CONNECTORS` tuple
- **Class naming**: Device connectors MUST implement `class DeviceConnector(DefaultDevice)`
- **Pytest isolation**: Classes named `TestPhase`, `TestflingerJob`, `TestEvent` have `__test__ = False` to prevent pytest collection

### Error Handling Patterns
- Device connectors raise `ProvisioningError` for recoverable failures, `RecoveryError` for fatal device issues
- Exit code 46 signals device requires manual intervention
- Agents handle timeouts via `GlobalTimeoutChecker` and `OutputTimeoutChecker` classes
- Server returns 404 with custom logging, 500 for MongoDB failures (see `server/src/testflinger/application.py`)

### Configuration Files
- Agent config: `testflinger-agent.conf` (see `agent/testflinger-agent.conf.example`)
- Server config: `testflinger.conf` or environment variables (see `server/testflinger.conf.example`)
- Device connector config: YAML files with device-specific schemas
- Job definitions: YAML/JSON with `job_queue`, `provision_data`, `test_data` sections

### Key Files to Reference
- `common/src/testflinger_common/enums.py`: Canonical state definitions
- `device-connectors/src/testflinger_device_connectors/devices/__init__.py`: Device connector base class (434 lines)
- `agent/src/testflinger_agent/job.py`: Job execution orchestration with masking/secrets
- `server/src/testflinger/application.py`: Flask app initialization with error handlers
- `CONTRIBUTING.md`: Monorepo structure and uv workflow

## Don't Do
- Never install dependencies with pip directly - always use `uv add`
- Don't run tests with `pytest` directly - use `uvx --with tox-uv tox -e unit`
- Don't manually edit `uv.lock` files
- Don't create device connectors without inheriting from `DefaultDevice`
- Don't assume subprojects share environments - each has its own venv
- Never commit without running `tox` in changed subprojects
- Don't use multi-line shell commands with `&&` - device connector commands are single-line strings

## Juju Deployment
Server and agent have Juju charms for k8s deployment:
- Server: `charmhub.io/testflinger-k8s` (see `server/charm/`)
- Agent host: `charmhub.io/testflinger-agent-host` (see `agent/charms/`)
- Local testing via terraform setups in `*/terraform/` directories
