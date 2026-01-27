"""Tests for agent configuration files.

These tests validate that agent TOML configuration files are well-formed,
contain all required fields, and have valid output schemas.
"""

import json
from pathlib import Path

import pytest

try:
    import tomllib
except ImportError:
    import tomli as tomllib


# Path to agents directory
AGENTS_DIR = Path(__file__).parent.parent / "agents"


class TestAgentConfigs:
    """Test agent configuration files are valid and well-formed."""

    def test_all_toml_files_parse_and_have_required_fields(self):
        """Verify all .toml files parse correctly and have required fields."""
        toml_files = list(AGENTS_DIR.glob("*.toml"))
        assert len(toml_files) > 0, "No TOML files found in agents directory"

        for toml_file in toml_files:
            with open(toml_file, "rb") as f:
                config = tomllib.load(f)

            assert config is not None, f"Empty config: {toml_file}"
            assert isinstance(config, dict)

            # Check required top-level fields for main config
            if "performance_profiler" in toml_file.name:
                for field in ["version", "model", "commands"]:
                    assert field in config, f"Missing {field} in {toml_file}"

                # Verify version is semver format
                version = config["version"]
                parts = version.split(".")
                assert len(parts) == 3, f"Version should be semver: {version}"
                assert all(p.isdigit() for p in parts)

    def test_output_schemas_are_valid_json(self):
        """Verify all output_schema fields are valid JSON with expected structure."""
        toml_files = list(AGENTS_DIR.glob("*.toml"))

        for toml_file in toml_files:
            with open(toml_file, "rb") as f:
                config = tomllib.load(f)

            if "commands" not in config:
                continue

            for cmd_name, cmd_config in config["commands"].items():
                if "output_schema" not in cmd_config:
                    continue

                schema_str = cmd_config["output_schema"]
                schema = json.loads(schema_str)
                assert isinstance(schema, dict), (
                    f"output_schema should be object in {toml_file}:{cmd_name}"
                )

                # Verify schema has properties
                if "properties" in schema:
                    props = schema["properties"]
                    assert isinstance(props, dict)

    def test_performance_profiler_command_structure(self):
        """Verify performance_profiler.toml has properly structured commands."""
        config_path = AGENTS_DIR / "performance_profiler.toml"
        if not config_path.exists():
            pytest.skip("performance_profiler.toml not found")

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        # Check commands section
        commands = config["commands"]
        assert isinstance(commands, dict)
        assert "performance_analysis" in commands

        cmd = commands["performance_analysis"]
        assert "description" in cmd
        assert "instructions" in cmd
        assert len(cmd["instructions"]) > 100  # Should be substantial

        # Verify instructions mention key concepts
        instructions = cmd["instructions"].lower()
        for concept in ["performance", "n+1", "async", "blocking"]:
            assert concept in instructions, f"Instructions should mention '{concept}'"

    def test_arguments_and_execution_strategy_valid(self):
        """Verify argument definitions and execution strategies are valid."""
        toml_files = list(AGENTS_DIR.glob("*.toml"))

        for toml_file in toml_files:
            with open(toml_file, "rb") as f:
                config = tomllib.load(f)

            if "commands" not in config:
                continue

            for cmd_name, cmd_config in config["commands"].items():
                # Check execution strategy if present
                if "execution_strategy" in cmd_config:
                    assert cmd_config["execution_strategy"] in ["plan", "act"]

                # Check arguments structure if present
                if "arguments" not in cmd_config:
                    continue

                args = cmd_config["arguments"]
                assert isinstance(args, list)

                for arg in args:
                    assert "name" in arg
                    assert "type" in arg
                    assert arg["type"] in ["string", "integer", "boolean", "array", "object"]
