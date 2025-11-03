# Example Device Connector Using New Base Classes

This example demonstrates how to use the new `BaseDeviceConnector` and
`DeviceConnectorProtocol` classes to create a device connector with
standardized patterns.

## Example 1: Minimal Connector Using New Base Classes

```python
"""Example device connector using new base classes."""

from testflinger_device_connectors.devices import DefaultDevice
from testflinger_device_connectors.devices.base import BaseDeviceConnector


class DeviceConnector(BaseDeviceConnector, DefaultDevice):
    """Example device connector demonstrating new patterns.
    
    This connector uses BaseDeviceConnector utilities for standardized
    configuration loading, logging, and error handling, while inheriting
    default implementations from DefaultDevice.
    """
    
    def __init__(self, config):
        """Initialize both base classes."""
        BaseDeviceConnector.__init__(self, config)
        DefaultDevice.__init__(self, config)
    
    def provision(self, args):
        """Provision device with standardized logging and error handling.
        
        This method demonstrates:
        - Using load_config() for standardized config loading
        - Using load_job_data() for standardized job data loading
        - Using run_phase() for consistent logging
        - Using helper methods for data extraction
        """
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        return self.run_phase(
            "provision",
            self._do_provision,
            config,
            job_data
        )
    
    def _do_provision(self, config, job_data):
        """Actual provisioning implementation.
        
        The logic is separated into this method so run_phase() can handle
        the BEGIN/END logging and error handling.
        """
        # Extract data using helper methods
        image_url = self.get_provision_data(job_data, "image_url")
        username = self.get_test_username(job_data)
        device_ip = config["device_ip"]
        
        logger.info(f"Provisioning {device_ip} with {image_url}")
        logger.info(f"Test username: {username}")
        
        # Your custom provisioning logic here
        # ...
        
        return 0  # Success
    
    def runtest(self, args):
        """Run tests with serial logging.
        
        This method demonstrates:
        - Creating a serial logger
        - Using run_phase() for test execution
        - Proper cleanup with finally block
        """
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        # Create serial logger
        serial_logger = self.create_serial_logger(
            config,
            filename="test-serial.log"
        )
        serial_logger.start()
        
        try:
            return self.run_phase(
                "test",
                self._run_tests,
                config,
                job_data
            )
        finally:
            serial_logger.stop()
    
    def _run_tests(self, config, job_data):
        """Run test commands."""
        test_cmds = self.get_test_data(job_data, "test_cmds")
        
        # Run your test commands
        # ...
        
        return 0  # Success
    
    # firmware_update, allocate, reserve, cleanup inherit from DefaultDevice
```

## Example 2: Custom Error Handling

```python
from testflinger_device_connectors.devices import (
    DefaultDevice,
    ProvisioningError,
    RecoveryError,
)
from testflinger_device_connectors.devices.base import BaseDeviceConnector


class DeviceConnector(BaseDeviceConnector, DefaultDevice):
    """Example with custom error handling."""
    
    def provision(self, args):
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        return self.run_phase(
            "provision",
            self._provision_with_retry,
            config,
            job_data
        )
    
    def _provision_with_retry(self, config, job_data):
        """Provision with retry logic and proper error handling."""
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                return self._attempt_provision(config, job_data)
            except ProvisioningError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}")
                    logger.info("Retrying...")
                    continue
                else:
                    logger.error("All provision attempts failed")
                    raise
        
        # Should not reach here
        return 1
    
    def _attempt_provision(self, config, job_data):
        """Single provision attempt."""
        # Check if device is responsive
        if not self._check_device_health(config):
            # Device is broken, needs manual intervention
            raise RecoveryError(
                "Device is unresponsive, exit code 46 will be returned"
            )
        
        # Try to provision
        success = self._do_actual_provision(config, job_data)
        
        if not success:
            # Recoverable error, can be retried
            raise ProvisioningError("Failed to provision device")
        
        return 0
    
    def _check_device_health(self, config):
        """Check if device is healthy."""
        # Your health check logic
        return True
    
    def _do_actual_provision(self, config, job_data):
        """Actual provisioning logic."""
        # Your provisioning logic
        return True
```

## Example 3: Complex Workflow with Multiple Phases

```python
from testflinger_device_connectors.devices import DefaultDevice
from testflinger_device_connectors.devices.base import BaseDeviceConnector


class DeviceConnector(BaseDeviceConnector, DefaultDevice):
    """Example with complex multi-phase workflow."""
    
    def provision(self, args):
        """Multi-step provisioning workflow."""
        config = self.load_config(args.config)
        job_data = self.load_job_data(args.job_data)
        
        # Run multiple sub-phases using run_phase
        phases = [
            ("validate_config", self._validate_config),
            ("prepare_device", self._prepare_device),
            ("install_image", self._install_image),
            ("configure_device", self._configure_device),
            ("verify_installation", self._verify_installation),
        ]
        
        for phase_name, phase_func in phases:
            exitcode = self.run_phase(
                phase_name,
                phase_func,
                config,
                job_data
            )
            if exitcode != 0:
                logger.error(f"Phase {phase_name} failed with exit code {exitcode}")
                return exitcode
        
        return 0
    
    def _validate_config(self, config, job_data):
        """Validate configuration before provisioning."""
        image_url = self.get_provision_data(job_data, "image_url")
        if not image_url:
            raise ProvisioningError("No image URL provided")
        return 0
    
    def _prepare_device(self, config, job_data):
        """Prepare device for provisioning."""
        # Your preparation logic
        return 0
    
    def _install_image(self, config, job_data):
        """Install OS image."""
        # Your installation logic
        return 0
    
    def _configure_device(self, config, job_data):
        """Configure device after installation."""
        # Your configuration logic
        return 0
    
    def _verify_installation(self, config, job_data):
        """Verify installation was successful."""
        # Your verification logic
        return 0
```

## Key Takeaways

1. **Separate Concerns**: Use `run_phase()` to wrap phase execution, keeping
   the actual logic in separate methods
   
2. **Use Helper Methods**: Take advantage of `get_provision_data()`,
   `get_test_data()`, `get_test_username()` for cleaner code
   
3. **Standardized Logging**: `run_phase()` provides consistent BEGIN/END
   logging automatically
   
4. **Proper Error Handling**: Use `ProvisioningError` for recoverable errors
   and `RecoveryError` for unrecoverable device failures
   
5. **Serial Logger Management**: Use `create_serial_logger()` for unified
   serial logger lifecycle
   
6. **Backward Compatible**: Inherit from both `BaseDeviceConnector` and
   `DefaultDevice` to get benefits of both

## Running the Examples

These examples are for demonstration purposes. To create a real connector:

1. Copy the example code to your connector module
2. Implement the actual provisioning/testing logic
3. Add any device-specific methods
4. Test with your device configuration
5. Verify all phases work correctly

For more information, see `docs/NEW_BASE_CLASSES.md`.
