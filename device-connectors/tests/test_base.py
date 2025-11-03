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
# along with this program.  If not, see <http://www.gnu.org/licenses/>
"""Tests for new base device connector classes."""

import json

import pytest
import yaml

from testflinger_device_connectors.devices import (
    ProvisioningError,
    RecoveryError,
)
from testflinger_device_connectors.devices.base import (
    BaseDeviceConnector,
    DeviceConnectorProtocol,
)


class TestDeviceConnectorProtocol:
    """Test the DeviceConnectorProtocol type checking."""

    def test_protocol_minimal_implementation(self):
        """Verify that a class with all required methods satisfies
        the protocol.
        """

        class MinimalConnector:
            config = {}

            def provision(self, args):
                return 0

            def firmware_update(self, args):
                return 0

            def runtest(self, args):
                return 0

            def allocate(self):
                pass

            def reserve(self, args):
                pass

            def cleanup(self, _):
                pass

        connector = MinimalConnector()
        assert isinstance(connector, DeviceConnectorProtocol)

    def test_protocol_missing_method(self):
        """Verify that a class missing required methods does not
        satisfy the protocol.
        """

        class IncompleteConnector:
            config = {}

            def provision(self, args):
                return 0

            # Missing other required methods

        connector = IncompleteConnector()
        assert not isinstance(connector, DeviceConnectorProtocol)


class TestBaseDeviceConnector:
    """Test the BaseDeviceConnector class utilities."""

    @pytest.fixture
    def base_connector(self):
        """Create a BaseDeviceConnector instance for testing."""
        config = {"device_ip": "10.0.0.1", "agent_name": "test_agent"}
        return BaseDeviceConnector(config)

    @pytest.fixture
    def config_file(self, tmp_path):
        """Create a temporary YAML config file."""
        config = {
            "device_ip": "192.168.1.100",
            "agent_name": "test_agent",
            "serial_host": "192.168.1.200",
            "serial_port": "5000",
        }
        config_path = tmp_path / "device.yaml"
        config_path.write_text(yaml.dump(config))
        return config_path

    @pytest.fixture
    def job_data_file(self, tmp_path):
        """Create a temporary JSON job data file."""
        job_data = {
            "job_id": "test-job-123",
            "provision_data": {"image_url": "http://example.com/image.iso"},
            "test_data": {
                "test_username": "testuser",
                "test_cmds": "echo hello",
            },
        }
        job_path = tmp_path / "job.json"
        job_path.write_text(json.dumps(job_data))
        return job_path

    def test_init(self, base_connector):
        """Test BaseDeviceConnector initialization."""
        assert base_connector.config["device_ip"] == "10.0.0.1"
        assert base_connector.config["agent_name"] == "test_agent"

    def test_load_config(self, base_connector, config_file):
        """Test loading configuration from YAML file."""
        config = base_connector.load_config(str(config_file))

        assert config["device_ip"] == "192.168.1.100"
        assert config["agent_name"] == "test_agent"
        assert config["serial_host"] == "192.168.1.200"
        assert config["serial_port"] == "5000"

    def test_load_config_file_not_found(self, base_connector):
        """Test loading config from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            base_connector.load_config("/nonexistent/config.yaml")

    def test_load_config_invalid_yaml(self, base_connector, tmp_path):
        """Test loading invalid YAML raises error."""
        invalid_yaml = tmp_path / "invalid.yaml"
        invalid_yaml.write_text("{ invalid yaml content")

        with pytest.raises(yaml.YAMLError):
            base_connector.load_config(str(invalid_yaml))

    def test_load_job_data(self, base_connector, job_data_file):
        """Test loading job data from JSON file."""
        job_data = base_connector.load_job_data(str(job_data_file))

        assert job_data["job_id"] == "test-job-123"
        assert "provision_data" in job_data
        assert "test_data" in job_data

    def test_load_job_data_file_not_found(self, base_connector):
        """Test loading job data from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            base_connector.load_job_data("/nonexistent/job.json")

    def test_load_job_data_invalid_json(self, base_connector, tmp_path):
        """Test loading invalid JSON raises error."""
        invalid_json = tmp_path / "invalid.json"
        invalid_json.write_text("{ invalid json content")

        with pytest.raises(json.JSONDecodeError):
            base_connector.load_job_data(str(invalid_json))

    def test_run_phase_success(self, base_connector):
        """Test run_phase with successful execution."""

        def successful_phase():
            return 0

        exitcode = base_connector.run_phase("test", successful_phase)
        assert exitcode == 0

    def test_run_phase_with_return_value(self, base_connector):
        """Test run_phase with non-zero return value."""

        def failing_phase():
            return 1

        exitcode = base_connector.run_phase("test", failing_phase)
        assert exitcode == 1

    def test_run_phase_with_none_return(self, base_connector):
        """Test run_phase with None return value (treated as success)."""

        def phase_no_return():
            pass

        exitcode = base_connector.run_phase("test", phase_no_return)
        assert exitcode == 0

    def test_run_phase_with_args(self, base_connector):
        """Test run_phase passes arguments correctly."""

        def phase_with_args(arg1, arg2, kwarg1=None):
            assert arg1 == "test1"
            assert arg2 == "test2"
            assert kwarg1 == "test3"
            return 0

        exitcode = base_connector.run_phase(
            "test",
            phase_with_args,
            "test1",
            "test2",
            kwarg1="test3",
        )
        assert exitcode == 0

    def test_run_phase_provisioning_error(self, base_connector):
        """Test run_phase re-raises ProvisioningError."""

        def failing_phase():
            raise ProvisioningError("Provisioning failed")

        with pytest.raises(ProvisioningError) as exc_info:
            base_connector.run_phase("provision", failing_phase)
        assert "Provisioning failed" in str(exc_info.value)

    def test_run_phase_recovery_error(self, base_connector):
        """Test run_phase re-raises RecoveryError."""

        def failing_phase():
            raise RecoveryError("Device needs recovery")

        with pytest.raises(RecoveryError) as exc_info:
            base_connector.run_phase("provision", failing_phase)
        assert "Device needs recovery" in str(exc_info.value)

    def test_run_phase_unexpected_error(self, base_connector):
        """Test run_phase re-raises unexpected errors."""

        def failing_phase():
            raise ValueError("Unexpected error")

        with pytest.raises(ValueError) as exc_info:
            base_connector.run_phase("provision", failing_phase)
        assert "Unexpected error" in str(exc_info.value)

    def test_create_serial_logger_with_config(self, base_connector):
        """Test creating a serial logger with full configuration."""
        config = {
            "serial_host": "192.168.1.1",
            "serial_port": "5000",
        }

        serial_logger = base_connector.create_serial_logger(
            config,
            "test.log",
        )

        # Should create a RealSerialLogger (not a stub)
        assert serial_logger is not None
        assert hasattr(serial_logger, "start")
        assert hasattr(serial_logger, "stop")

    def test_create_serial_logger_without_config(self, base_connector):
        """Test creating a serial logger without configuration."""
        config = {}

        serial_logger = base_connector.create_serial_logger(
            config,
            "test.log",
        )

        # Should create a StubSerialLogger
        assert serial_logger is not None
        assert hasattr(serial_logger, "start")
        assert hasattr(serial_logger, "stop")

    def test_get_provision_data_full(self, base_connector):
        """Test getting full provision_data dictionary."""
        job_data = {
            "provision_data": {"image": "ubuntu.iso", "url": "http://..."}
        }

        provision_data = base_connector.get_provision_data(job_data)
        assert provision_data == {"image": "ubuntu.iso", "url": "http://..."}

    def test_get_provision_data_with_key(self, base_connector):
        """Test getting specific key from provision_data."""
        job_data = {
            "provision_data": {"image": "ubuntu.iso", "url": "http://..."}
        }

        image = base_connector.get_provision_data(job_data, "image")
        assert image == "ubuntu.iso"

    def test_get_provision_data_missing_key(self, base_connector):
        """Test getting non-existent key from provision_data."""
        job_data = {"provision_data": {"image": "ubuntu.iso"}}

        value = base_connector.get_provision_data(job_data, "nonexistent")
        assert value is None

    def test_get_provision_data_empty(self, base_connector):
        """Test getting provision_data when not present."""
        job_data = {}

        provision_data = base_connector.get_provision_data(job_data)
        assert provision_data == {}

    def test_get_test_data_full(self, base_connector):
        """Test getting full test_data dictionary."""
        job_data = {"test_data": {"test_cmds": "echo hello", "timeout": 3600}}

        test_data = base_connector.get_test_data(job_data)
        assert test_data == {"test_cmds": "echo hello", "timeout": 3600}

    def test_get_test_data_with_key(self, base_connector):
        """Test getting specific key from test_data."""
        job_data = {"test_data": {"test_cmds": "echo hello", "timeout": 3600}}

        test_cmds = base_connector.get_test_data(job_data, "test_cmds")
        assert test_cmds == "echo hello"

    def test_get_test_data_missing_key(self, base_connector):
        """Test getting non-existent key from test_data."""
        job_data = {"test_data": {"test_cmds": "echo hello"}}

        value = base_connector.get_test_data(job_data, "nonexistent")
        assert value is None

    def test_get_test_data_empty(self, base_connector):
        """Test getting test_data when not present."""
        job_data = {}

        test_data = base_connector.get_test_data(job_data)
        assert test_data == {}

    def test_get_test_username_default(self, base_connector):
        """Test getting test username with default value."""
        job_data = {"test_data": {}}

        username = base_connector.get_test_username(job_data)
        assert username == "ubuntu"

    def test_get_test_username_custom(self, base_connector):
        """Test getting custom test username."""
        job_data = {"test_data": {"test_username": "customuser"}}

        username = base_connector.get_test_username(job_data)
        assert username == "customuser"

    def test_get_test_username_missing_test_data(self, base_connector):
        """Test getting test username when test_data is missing."""
        job_data = {}

        username = base_connector.get_test_username(job_data)
        assert username == "ubuntu"


class TestBaseDeviceConnectorIntegration:
    """Integration tests for BaseDeviceConnector with real files."""

    def test_full_workflow(self, tmp_path):
        """Test a complete workflow using BaseDeviceConnector."""
        # Create config file
        config = {
            "device_ip": "192.168.1.100",
            "agent_name": "test_agent",
        }
        config_path = tmp_path / "device.yaml"
        config_path.write_text(yaml.dump(config))

        # Create job data file
        job_data = {
            "job_id": "test-job-123",
            "provision_data": {"image_url": "http://example.com/image.iso"},
            "test_data": {
                "test_username": "testuser",
                "test_cmds": "echo hello",
            },
        }
        job_path = tmp_path / "job.json"
        job_path.write_text(json.dumps(job_data))

        # Create connector and load data
        connector = BaseDeviceConnector(config)
        loaded_config = connector.load_config(str(config_path))
        loaded_job_data = connector.load_job_data(str(job_path))

        # Verify data was loaded correctly
        assert loaded_config["device_ip"] == "192.168.1.100"
        assert loaded_job_data["job_id"] == "test-job-123"

        # Test helper methods
        username = connector.get_test_username(loaded_job_data)
        assert username == "testuser"

        image_url = connector.get_provision_data(
            loaded_job_data,
            "image_url",
        )
        assert image_url == "http://example.com/image.iso"
