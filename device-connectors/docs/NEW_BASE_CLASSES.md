# New Base Classes for Device Connectors

This document describes the new base classes introduced in Phase 1 of the device connector refactoring. These classes provide standardized patterns for common device connector operations.

## Overview

The new base classes are **additive** and designed to **coexist** with the existing `DefaultDevice` class. All existing device connectors continue to work without changes. The new classes are:

1. **`DeviceConnectorProtocol`** - A Protocol (PEP 544) defining the expected interface
2. **`BaseDeviceConnector`** - A base class with standardized utilities

## DeviceConnectorProtocol

A runtime-checkable Protocol that defines the expected interface for all device connectors. This can be used for type checking and runtime validation.

### Interface

All device connectors should implement the following methods:

- `provision(args) -> int` - Provision the device with an OS
- `firmware_update(args) -> int` - Update device firmware
- `runtest(args) -> int` - Run test commands on the device
- `allocate() -> None` - Allocate devices for multi-agent jobs
- `reserve(args) -> None` - Reserve device for interactive access
- `cleanup(_) -> None` - Clean up device after job completion

### Usage

```python
from testflinger_device_connectors.devices.base import DeviceConnectorProtocol

# Type checking
def process_connector(connector: DeviceConnectorProtocol):
    connector.provision(args)

# Runtime checking
if isinstance(my_connector, DeviceConnectorProtocol):
    print("Connector implements the required interface")
```

## BaseDeviceConnector

A base class providing standardized utilities that all device connectors can use. This class provides:

- **Configuration loading** - Standardized YAML config loading
- **Job data loading** - Standardized JSON job data loading
- **Phase execution** - Consistent logging and error handling
- **Serial logger management** - Unified serial logger lifecycle
- **Helper methods** - Common data extraction utilities

### Key Methods

#### Configuration and Data Loading

```python
config = self.load_config(args.config)
# Loads YAML config with error handling

job_data = self.load_job_data(args.job_data)
# Loads JSON job data with error handling
```

#### Phase Execution with Standardized Logging

```python
def provision(self, args):
    config = self.load_config(args.config)
    job_data = self.load_job_data(args.job_data)
    
    return self.run_phase(
        "provision",
        self._do_provision,
        config,
        job_data
    )

def _do_provision(self, config, job_data):
    # Your provisioning logic here
    return 0
```

The `run_phase()` method automatically:
- Logs "BEGIN <phase_name>" at the start
- Logs "END <phase_name>" on success
- Handles errors and logs them with context
- Re-raises `ProvisioningError` and `RecoveryError`

#### Serial Logger Management

```python
serial_logger = self.create_serial_logger(
    config,
    filename="test-serial.log"
)
serial_logger.start()
try:
    # Run tests
    pass
finally:
    serial_logger.stop()
```

#### Data Extraction Helpers

```python
# Get provision data
provision_data = self.get_provision_data(job_data)
image_url = self.get_provision_data(job_data, "image_url")

# Get test data
test_data = self.get_test_data(job_data)
test_cmds = self.get_test_data(job_data, "test_cmds")

# Get test username (defaults to "ubuntu")
username = self.get_test_username(job_data)
```

## Usage Patterns

### Pattern 1: Using BaseDeviceConnector with DefaultDevice

The recommended pattern for new connectors:

```python
from testflinger_device_connectors.devices import DefaultDevice
from testflinger_device_connectors.devices.base import BaseDeviceConnector

class DeviceConnector(BaseDeviceConnector, DefaultDevice):
    """My device connector with standardized utilities."""
    
    def __init__(self, config):
        # Initialize both base classes
        BaseDeviceConnector.__init__(self, config)
        DefaultDevice.__init__(self, config)
    
    def provision(self, args):
        """Provision with standardized logging and error handling."""
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        return self.run_phase(
            "provision",
            self._do_provision,
            config,
            job_data
        )
    
    def _do_provision(self, config, job_data):
        """Actual provisioning logic."""
        # Get data using helper methods
        image_url = self.get_provision_data(job_data, "image_url")
        username = self.get_test_username(job_data)
        
        # Your provisioning code here
        return 0
```

### Pattern 2: Using BaseDeviceConnector Standalone

For simple connectors that don't need DefaultDevice's features:

```python
from testflinger_device_connectors.devices.base import BaseDeviceConnector

class DeviceConnector(BaseDeviceConnector):
    """Minimal device connector using only new base utilities."""
    
    def provision(self, args):
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        return self.run_phase(
            "provision",
            self._provision_impl,
            config,
            job_data
        )
    
    def _provision_impl(self, config, job_data):
        # Your custom provisioning logic
        return 0
    
    # Implement other required methods
    def firmware_update(self, args):
        return 0  # Or inherit from DefaultDevice
    
    def runtest(self, args):
        # Use DefaultDevice.runtest or implement custom
        pass
    
    def allocate(self):
        pass
    
    def reserve(self, args):
        pass
    
    def cleanup(self, _):
        pass
```

### Pattern 3: Existing Connectors (No Changes Required)

Existing connectors continue to work without modification:

```python
from testflinger_device_connectors.devices import DefaultDevice

class DeviceConnector(DefaultDevice):
    """Existing connector - works as before."""
    
    def provision(self, args):
        # Your existing code
        pass
```

## Error Handling

The new base classes standardize error handling:

### Exit Code 46

Exit code 46 indicates unrecoverable device failure requiring manual intervention. Use `RecoveryError`:

```python
from testflinger_device_connectors.devices import RecoveryError

if device_is_broken:
    raise RecoveryError("Device hardware failure detected")
```

### Provisioning Errors

For recoverable provisioning failures:

```python
from testflinger_device_connectors.devices import ProvisioningError

if provision_failed:
    raise ProvisioningError("Failed to download image")
```

### Other Errors

Other exceptions are logged with context and re-raised for proper handling by the agent.

## Benefits

1. **Consistency** - All connectors using the base classes follow the same patterns
2. **Less Code** - Common operations are centralized
3. **Better Logging** - Standardized log messages make debugging easier
4. **Type Safety** - Protocol provides type checking support
5. **Maintainability** - Updates to common patterns can be made in one place
6. **Backward Compatible** - Existing connectors work without changes
7. **Documentation** - Clear interface expectations

## Migration Guide

Migration to the new base classes is **optional**. To migrate:

1. Import `BaseDeviceConnector`
2. Add it as a parent class alongside `DefaultDevice`
3. Use helper methods like `load_config()`, `load_job_data()`
4. Wrap phase execution in `run_phase()` for consistent logging
5. Use data extraction helpers like `get_provision_data()`

Example migration:

**Before:**
```python
class DeviceConnector(DefaultDevice):
    def provision(self, args):
        with open(args.config) as f:
            config = yaml.safe_load(f)
        with open(args.job_data) as f:
            job_data = json.load(f)
        
        logger.info("BEGIN provision")
        # ... provisioning logic ...
        logger.info("END provision")
        return 0
```

**After:**
```python
class DeviceConnector(BaseDeviceConnector, DefaultDevice):
    def provision(self, args):
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        return self.run_phase("provision", self._do_provision, config, job_data)
    
    def _do_provision(self, config, job_data):
        # ... provisioning logic ...
        return 0
```

## Testing

The new base classes have comprehensive test coverage:
- Protocol validation tests
- Configuration loading tests
- Job data loading tests
- Phase execution and error handling tests
- Serial logger creation tests
- Helper method tests

Run tests:
```bash
pytest tests/test_base.py -v
```

## Next Steps

Phase 1 establishes the foundation. Future phases will:
- Refactor example connectors to demonstrate the patterns
- Create migration documentation
- Gradually migrate existing connectors
- Eventually deprecate old patterns in a future major version

## Questions?

For questions or issues with the new base classes, please refer to:
- The issue tracker: https://github.com/rene-oromtz/testflinger/issues/2
- The source code: `device-connectors/src/testflinger_device_connectors/devices/base.py`
- The tests: `device-connectors/tests/test_base.py`
