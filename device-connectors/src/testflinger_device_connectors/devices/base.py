# Copyright (C) 2024 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""New base classes for standardized device connector patterns.

This module provides enhanced base classes for device connectors that
standardize common patterns like configuration loading, error handling,
and serial logger management. These classes are additive and coexist
with the existing DefaultDevice class for backward compatibility.
"""

import json
import logging
from typing import Any, Callable, Optional, Protocol, runtime_checkable

import yaml

from testflinger_device_connectors.devices import (
    ProvisioningError,
    RecoveryError,
    SerialLogger,
)

logger = logging.getLogger(__name__)


@runtime_checkable
class DeviceConnectorProtocol(Protocol):
    """Protocol defining the expected interface for device connectors.

    This protocol can be used for type checking and to verify that a
    device connector implements the required methods. All methods that
    accept `args` expect an argparse.Namespace object with at minimum:
    - config: str - Path to the device configuration YAML file
    - job_data: str - Path to the job data JSON file

    Exit code 46 from any phase indicates unrecoverable device failure
    and requires manual intervention.
    """

    config: dict

    def provision(self, args) -> int:
        """Provision the device with an operating system.

        :param args: Arguments containing config and job_data paths
        :return: Exit code (0 for success, non-zero for failure)
        :raises ProvisioningError: For recoverable provisioning failures
        :raises RecoveryError: For unrecoverable device failures
        """
        ...

    def firmware_update(self, args) -> int:
        """Update the device firmware.

        :param args: Arguments containing config and job_data paths
        :return: Exit code (0 for success, non-zero for failure)
        """
        ...

    def runtest(self, args) -> int:
        """Run test commands on the device.

        :param args: Arguments containing config and job_data paths
        :return: Exit code (0 for success, non-zero for failure)
        """
        ...

    def allocate(self) -> None:
        """Allocate devices for multi-agent jobs.

        This method is called before provisioning in multi-device setups.
        """
        ...

    def reserve(self, args) -> None:
        """Reserve the device for interactive access.

        :param args: Arguments containing config and job_data paths
        """
        ...

    def cleanup(self, _) -> None:
        """Clean up the device after job completion.

        :param _: Unused parameter for backward compatibility
        """
        ...


class BaseDeviceConnector:
    """Base class providing standardized utilities for device connectors.

    This class provides common infrastructure for all device connectors:
    - Standardized configuration and job data loading
    - Consistent logging patterns for phase execution
    - Unified serial logger lifecycle management
    - Type hints and comprehensive documentation

    This class is designed to be used alongside DefaultDevice for
    backward compatibility. New connectors should consider inheriting
    from this class and DefaultDevice to get both sets of functionality.

    Example usage:
        ```python
        from testflinger_device_connectors.devices import DefaultDevice
        from testflinger_device_connectors.devices.base import (
            BaseDeviceConnector
        )

        class DeviceConnector(BaseDeviceConnector, DefaultDevice):
            def provision(self, args):
                config = self.load_config(args.config)
                job_data = self.load_job_data(args.job_data)
                return self.run_phase("provision", self._do_provision,
                                      config, job_data)

            def _do_provision(self, config, job_data):
                # Actual provisioning logic here
                pass
        ```

    Attributes:
        config: Device configuration dictionary loaded from YAML
    """

    def __init__(self, config: dict) -> None:
        """Initialize the base device connector.

        :param config: Device configuration dictionary
        """
        self.config = config

    def load_config(self, config_path: str) -> dict:
        """Load device configuration from a YAML file.

        Provides standardized configuration loading with error handling.

        :param config_path: Path to the YAML configuration file
        :return: Dictionary containing device configuration
        :raises FileNotFoundError: If config file doesn't exist
        :raises yaml.YAMLError: If config file is invalid YAML
        """
        logger.debug("Loading configuration from: %s", config_path)
        with open(config_path, encoding="utf-8") as configfile:
            config = yaml.safe_load(configfile)
        return config

    def load_job_data(self, job_data_path: str) -> dict:
        """Load job data from a JSON file.

        Provides standardized job data loading with error handling.

        :param job_data_path: Path to the JSON job data file
        :return: Dictionary containing job data
        :raises FileNotFoundError: If job data file doesn't exist
        :raises json.JSONDecodeError: If job data file is invalid JSON
        """
        logger.debug("Loading job data from: %s", job_data_path)
        with open(job_data_path, encoding="utf-8") as job_json:
            job_data = json.load(job_json)
        return job_data

    def run_phase(
        self,
        phase_name: str,
        phase_func: Callable,
        *args,
        **kwargs,
    ) -> int:
        """Execute a phase with standardized logging and error handling.

        This method wraps phase execution with consistent logging and
        error handling patterns. It logs phase start/end, catches and
        re-raises exceptions with context, and ensures proper cleanup.

        :param phase_name: Name of the phase (e.g., "provision", "test")
        :param phase_func: Function to execute for this phase
        :param args: Positional arguments to pass to phase_func
        :param kwargs: Keyword arguments to pass to phase_func
        :return: Exit code (0 for success, non-zero for failure)
        :raises ProvisioningError: For recoverable failures
        :raises RecoveryError: For unrecoverable device failures
        """
        logger.info("BEGIN %s", phase_name)
        try:
            result = phase_func(*args, **kwargs)
            # Handle both int return values and None
            exitcode = result if isinstance(result, int) else 0
            logger.info("END %s", phase_name)
            return exitcode
        except (ProvisioningError, RecoveryError) as e:
            logger.error("%s failed: %s", phase_name, str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error in %s: %s", phase_name, str(e))
            raise

    def create_serial_logger(
        self,
        config: dict,
        filename: str = "serial.log",
    ) -> Any:
        """Create a serial logger instance from configuration.

        Creates either a real or stub serial logger based on whether
        serial logging configuration is present.

        :param config: Device configuration dictionary
        :param filename: Output filename for serial logs
        :return: SerialLogger instance (real or stub)
        """
        serial_host = config.get("serial_host")
        serial_port = config.get("serial_port")
        return SerialLogger(serial_host, serial_port, filename)

    def get_provision_data(
        self,
        job_data: dict,
        key: Optional[str] = None,
    ) -> Any:
        """Extract provision data from job data.

        Helper method to safely access provision_data with optional
        nested key access.

        :param job_data: Job data dictionary
        :param key: Optional key to extract from provision_data
        :return: Full provision_data dict or specific value if key given
        """
        provision_data = job_data.get("provision_data", {})
        if key:
            return provision_data.get(key)
        return provision_data

    def get_test_data(
        self,
        job_data: dict,
        key: Optional[str] = None,
    ) -> Any:
        """Extract test data from job data.

        Helper method to safely access test_data with optional
        nested key access.

        :param job_data: Job data dictionary
        :param key: Optional key to extract from test_data
        :return: Full test_data dict or specific value if key is given
        """
        test_data = job_data.get("test_data", {})
        if key:
            return test_data.get(key)
        return test_data

    def get_test_username(self, job_data: dict) -> str:
        """Get the test username from job data.

        :param job_data: Job data dictionary
        :return: Test username (defaults to "ubuntu" if not specified)
        """
        return self.get_test_data(job_data, "test_username") or "ubuntu"
