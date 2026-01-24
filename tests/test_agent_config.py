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


class TestPerformanceProfilerConfig:
    """Test performance_profiler.toml configuration."""

    @pytest.fixture
    def config(self):
        """Load the performance profiler configuration."""
        config_path = AGENTS_DIR / "performance_profiler.toml"
        assert config_path.exists(), f"Config file not found: {config_path}"

        with open(config_path, "rb") as f:
            return tomllib.load(f)

    def test_config_loads_successfully(self, config):
        """Verify the TOML file parses without errors."""
        assert config is not None
        assert isinstance(config, dict)

    def test_required_top_level_fields(self, config):
        """Verify required top-level fields are present."""
        required_fields = ["version", "model", "commands"]
        for field in required_fields:
            assert field in config, f"Missing required field: {field}"

    def test_version_format(self, config):
        """Verify version follows semantic versioning."""
        version = config["version"]
        assert isinstance(version, str)
        parts = version.split(".")
        assert len(parts) == 3, f"Version should be semver format: {version}"
        for part in parts:
            assert part.isdigit(), f"Version parts should be numeric: {version}"

    def test_model_specified(self, config):
        """Verify model is specified."""
        model = config["model"]
        assert isinstance(model, str)
        assert len(model) > 0

    def test_commands_structure(self, config):
        """Verify commands section has proper structure."""
        commands = config["commands"]
        assert isinstance(commands, dict)
        assert len(commands) > 0

        # Check for performance_analysis command
        assert "performance_analysis" in commands

    def test_performance_analysis_command(self, config):
        """Verify performance_analysis command configuration."""
        cmd = config["commands"]["performance_analysis"]

        # Required fields
        assert "description" in cmd
        assert isinstance(cmd["description"], str)
        assert len(cmd["description"]) > 0

        assert "instructions" in cmd
        assert isinstance(cmd["instructions"], str)
        assert len(cmd["instructions"]) > 100  # Should be substantial

    def test_instructions_content(self, config):
        """Verify instructions contain key information."""
        instructions = config["commands"]["performance_analysis"]["instructions"]

        # Should mention key concepts
        key_concepts = [
            "performance",
            "N+1",
            "async",
            "blocking",
            "memory",
            "optimization",
            "severity",
            "CRITICAL",
            "HIGH",
        ]

        for concept in key_concepts:
            assert concept.lower() in instructions.lower(), (
                f"Instructions should mention '{concept}'"
            )

    def test_execution_strategy(self, config):
        """Verify execution strategy is valid."""
        cmd = config["commands"]["performance_analysis"]

        if "execution_strategy" in cmd:
            strategy = cmd["execution_strategy"]
            assert strategy in ["plan", "act"], f"Invalid strategy: {strategy}"

    def test_arguments_structure(self, config):
        """Verify arguments are properly defined."""
        cmd = config["commands"]["performance_analysis"]

        if "arguments" in cmd:
            args = cmd["arguments"]
            assert isinstance(args, list)

            # Should have file_path and/or source_code arguments
            arg_names = [arg.get("name") for arg in args]
            assert "file_path" in arg_names or "source_code" in arg_names

            # Validate each argument structure
            for arg in args:
                assert "name" in arg
                assert "type" in arg
                assert arg["type"] in ["string", "integer", "boolean", "array", "object"]

                if "required" in arg:
                    assert isinstance(arg["required"], bool)

                if "description" in arg:
                    assert isinstance(arg["description"], str)


class TestOutputSchema:
    """Test output schema is valid JSON Schema."""

    @pytest.fixture
    def output_schema(self):
        """Load and parse the output schema."""
        config_path = AGENTS_DIR / "performance_profiler.toml"

        with open(config_path, "rb") as f:
            config = tomllib.load(f)

        cmd = config["commands"]["performance_analysis"]
        assert "output_schema" in cmd, "output_schema not found in config"

        schema_str = cmd["output_schema"]
        return json.loads(schema_str)

    def test_output_schema_is_valid_json(self, output_schema):
        """Verify output_schema is valid JSON."""
        assert output_schema is not None
        assert isinstance(output_schema, dict)

    def test_output_schema_has_properties(self, output_schema):
        """Verify schema has properties definition."""
        assert "properties" in output_schema
        assert isinstance(output_schema["properties"], dict)

    def test_required_output_properties(self, output_schema):
        """Verify required output properties are defined."""
        props = output_schema["properties"]

        required_props = [
            "success",
            "file_analyzed",
            "summary",
            "critical_issues",
            "high_priority_issues",
        ]

        for prop in required_props:
            assert prop in props, f"Missing required property: {prop}"

    def test_success_property(self, output_schema):
        """Verify success property is boolean."""
        success = output_schema["properties"]["success"]
        assert success.get("type") == "boolean"

    def test_summary_property_structure(self, output_schema):
        """Verify summary property has expected structure."""
        summary = output_schema["properties"]["summary"]
        assert summary.get("type") == "object"

        if "properties" in summary:
            summary_props = summary["properties"]
            expected = ["total_issues", "by_severity", "by_category"]
            for prop in expected:
                assert prop in summary_props, f"Summary missing property: {prop}"

    def test_critical_issues_property(self, output_schema):
        """Verify critical_issues is an array with proper item schema."""
        critical = output_schema["properties"]["critical_issues"]
        assert critical.get("type") == "array"

        if "items" in critical:
            items = critical["items"]
            assert items.get("type") == "object"

            if "properties" in items:
                item_props = items["properties"]
                expected = ["category", "line_number", "description"]
                for prop in expected:
                    assert prop in item_props, f"Critical issue item missing: {prop}"

    def test_optimization_roadmap_property(self, output_schema):
        """Verify optimization_roadmap has action arrays."""
        props = output_schema["properties"]

        if "optimization_roadmap" in props:
            roadmap = props["optimization_roadmap"]
            assert roadmap.get("type") == "object"

            if "properties" in roadmap:
                roadmap_props = roadmap["properties"]
                expected = [
                    "immediate_actions",
                    "short_term_improvements",
                    "long_term_enhancements",
                ]
                for prop in expected:
                    assert prop in roadmap_props, f"Roadmap missing: {prop}"

    def test_risk_assessment_property(self, output_schema):
        """Verify risk_assessment has expected fields."""
        props = output_schema["properties"]

        if "risk_assessment" in props:
            risk = props["risk_assessment"]
            assert risk.get("type") == "object"

            if "properties" in risk:
                risk_props = risk["properties"]
                expected = [
                    "performance_degradation_risk",
                    "scalability_concerns",
                    "production_readiness",
                ]
                for prop in expected:
                    assert prop in risk_props, f"Risk assessment missing: {prop}"


class TestKeywordAnalysisConfig:
    """Test keyword_analysis.toml configuration (if exists)."""

    @pytest.fixture
    def config(self):
        """Load the keyword analysis configuration."""
        config_path = AGENTS_DIR / "keyword_analysis.toml"
        if not config_path.exists():
            pytest.skip("keyword_analysis.toml not found")

        with open(config_path, "rb") as f:
            return tomllib.load(f)

    def test_config_loads_successfully(self, config):
        """Verify the TOML file parses without errors."""
        assert config is not None
        assert isinstance(config, dict)

    def test_has_commands_section(self, config):
        """Verify commands section exists."""
        assert "commands" in config or "version" in config


class TestAllAgentConfigs:
    """Test that all agent config files in the directory are valid."""

    def test_all_toml_files_parse(self):
        """Verify all .toml files in agents directory parse correctly."""
        toml_files = list(AGENTS_DIR.glob("*.toml"))
        assert len(toml_files) > 0, "No TOML files found in agents directory"

        for toml_file in toml_files:
            try:
                with open(toml_file, "rb") as f:
                    config = tomllib.load(f)
                assert config is not None, f"Empty config: {toml_file}"
            except Exception as e:
                pytest.fail(f"Failed to parse {toml_file}: {e}")

    def test_no_syntax_errors_in_instructions(self):
        """Verify instructions don't have obvious syntax issues."""
        toml_files = list(AGENTS_DIR.glob("*.toml"))

        for toml_file in toml_files:
            with open(toml_file, "rb") as f:
                config = tomllib.load(f)

            if "commands" not in config:
                continue

            for cmd_name, cmd_config in config["commands"].items():
                if "instructions" not in cmd_config:
                    continue

                instructions = cmd_config["instructions"]

                # Check for unbalanced braces (common issue)
                open_braces = instructions.count("{")
                close_braces = instructions.count("}")

                # Allow some imbalance for template placeholders
                assert abs(open_braces - close_braces) <= 10, (
                    f"Possible unbalanced braces in {toml_file}:{cmd_name}"
                )

    def test_output_schemas_are_valid_json(self):
        """Verify all output_schema fields are valid JSON."""
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
                try:
                    schema = json.loads(schema_str)
                    assert isinstance(schema, dict), (
                        f"output_schema should be object in {toml_file}:{cmd_name}"
                    )
                except json.JSONDecodeError as e:
                    pytest.fail(
                        f"Invalid JSON in output_schema for {toml_file}:{cmd_name}: {e}"
                    )
