#!/opt/homebrew/bin/python3.12
"""
Workshop MCP Verification Script

This script verifies that all prerequisites and components are properly installed
and configured for the Python MCP Agent Workshop.
"""

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Any
import importlib.util


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


class WorkshopVerifier:
    """Comprehensive verification system for the MCP workshop setup."""
    
    def __init__(self) -> None:
        """Initialize the verifier."""
        self.project_root = Path(__file__).parent
        self.results: List[Tuple[str, bool, str]] = []
        self.errors: List[str] = []
    
    def print_header(self, title: str) -> None:
        """Print a formatted section header."""
        print(f"\n{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{title.center(60)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'='*60}{Colors.END}\n")
    
    def print_result(self, test_name: str, success: bool, message: str = "") -> None:
        """Print a test result with colored output."""
        status_icon = f"{Colors.GREEN}✅{Colors.END}" if success else f"{Colors.RED}❌{Colors.END}"
        status_text = f"{Colors.GREEN}PASS{Colors.END}" if success else f"{Colors.RED}FAIL{Colors.END}"
        
        print(f"{status_icon} {test_name:<40} [{status_text}]")
        
        if message:
            color = Colors.GREEN if success else Colors.RED
            print(f"   {color}{message}{Colors.END}")
        
        self.results.append((test_name, success, message))
        
        if not success:
            self.errors.append(f"{test_name}: {message}")
    
    def run_command(self, command: List[str], capture_output: bool = True, timeout: int = 30) -> Tuple[bool, str]:
        """Run a shell command and return success status and output."""
        try:
            result = subprocess.run(
                command,
                capture_output=capture_output,
                text=True,
                timeout=timeout,
                cwd=self.project_root
            )
            return result.returncode == 0, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout} seconds"
        except FileNotFoundError:
            return False, f"Command not found: {command[0]}"
        except Exception as e:
            return False, f"Error running command: {str(e)}"
    
    def check_python_version(self) -> None:
        """Verify Python version is 3.11 or higher."""
        self.print_header("Python Version Check")
        
        version_info = sys.version_info
        print(version_info)
        current_version = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
        
        if version_info >= (3, 11):
            self.print_result(
                "Python Version",
                True,
                f"Python {current_version} (meets requirement: 3.11+)"
            )
        else:
            self.print_result(
                "Python Version",
                False,
                f"Python {current_version} (requires 3.11+)"
            )
    
    def check_poetry_installation(self) -> None:
        """Verify Poetry is installed and functional."""
        self.print_header("Poetry Installation Check")
        
        # Check if poetry command exists
        success, output = self.run_command(["poetry", "--version"])
        
        if success:
            version = output.strip()
            self.print_result("Poetry Installation", True, version)
            
            # Check poetry configuration
            success, output = self.run_command(["poetry", "config", "--list"])
            if success:
                self.print_result("Poetry Configuration", True, "Configuration accessible")
            else:
                self.print_result("Poetry Configuration", False, "Cannot access configuration")
        else:
            self.print_result(
                "Poetry Installation",
                False,
                "Poetry not found. Install from https://python-poetry.org/docs/#installation"
            )
    
    def check_project_structure(self) -> None:
        """Verify the project structure is correct."""
        self.print_header("Project Structure Check")
        
        required_files = [
            "pyproject.toml",
            "README.md",
            "src/workshop_mcp/__init__.py",
            "src/workshop_mcp/server.py",
            "src/workshop_mcp/keyword_search.py",
            "agents/sum_agent.toml",
            "tests/__init__.py",
            "tests/test_keyword_search.py",
            ".gitignore"
        ]
        
        for file_path in required_files:
            full_path = self.project_root / file_path
            exists = full_path.exists()
            
            self.print_result(
                f"File: {file_path}",
                exists,
                "Found" if exists else "Missing"
            )
    
    def check_dependencies(self) -> None:
        """Check if dependencies can be installed."""
        self.print_header("Dependency Installation Check")
        
        # Check if pyproject.toml exists
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            self.print_result("pyproject.toml", False, "File not found")
            return
        
        # Try to install dependencies
        success, output = self.run_command(["poetry", "install"], timeout=120)
        
        if success:
            self.print_result("Dependency Installation", True, "All dependencies installed")
            
            # Verify key dependencies are importable
            key_deps = ["mcp", "aiofiles", "pytest"]
            
            for dep in key_deps:
                success, _ = self.run_command(["poetry", "run", "python", "-c", f"import {dep}"])
                self.print_result(
                    f"Import {dep}",
                    success,
                    "Available" if success else "Import failed"
                )
        else:
            self.print_result(
                "Dependency Installation",
                False,
                f"Installation failed: {output[:200]}..."
            )
    
    def check_mcp_server_startup(self) -> None:
        """Test if the MCP server can start up."""
        self.print_header("MCP Server Startup Check")
        
        # Create a simple test script to check server startup
        test_script = '''
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_server():
    try:
        from workshop_mcp.server import WorkshopMCPServer
        server = WorkshopMCPServer()
        print("Server created successfully")
        return True
    except Exception as e:
        print(f"Server creation failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_server())
    sys.exit(0 if result else 1)
'''
        
        # Write test script to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_script_path = f.name
        
        try:
            success, output = self.run_command(["poetry", "run", "python", test_script_path])
            
            self.print_result(
                "MCP Server Creation",
                success,
                "Server can be instantiated" if success else f"Error: {output[:100]}..."
            )
        finally:
            os.unlink(test_script_path)
    
    def check_keyword_search_functionality(self) -> None:
        """Test the keyword search functionality."""
        self.print_header("Keyword Search Functionality Check")
        
        # Create a test script for keyword search
        test_script = '''
import asyncio
import sys
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_keyword_search():
    try:
        from workshop_mcp.keyword_search import KeywordSearchTool
        
        # Create temporary test directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create test file
            test_file = temp_path / "test.py"
            test_file.write_text("def hello():\\n    return \\"world\\"")
            
            # Test search
            tool = KeywordSearchTool()
            result = await tool.execute("world", [str(temp_path)])
            
            # Verify result
            if result["summary"]["total_occurrences"] > 0:
                print("Keyword search working correctly")
                return True
            else:
                print("No occurrences found in test")
                return False
                
    except Exception as e:
        print(f"Keyword search test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_keyword_search())
    sys.exit(0 if result else 1)
'''
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(test_script)
            test_script_path = f.name
        
        try:
            success, output = self.run_command(["poetry", "run", "python", test_script_path])
            
            self.print_result(
                "Keyword Search Test",
                success,
                "Functionality working" if success else f"Error: {output[:100]}..."
            )
        finally:
            os.unlink(test_script_path)
    
    def run_unit_tests(self) -> None:
        """Run the unit test suite."""
        self.print_header("Unit Tests Check")
        
        # Check if pytest is available
        success, output = self.run_command(["poetry", "run", "pytest", "--version"])
        
        if not success:
            self.print_result("Pytest Availability", False, "Pytest not available")
            return
        
        self.print_result("Pytest Availability", True, "Pytest available")
        
        # Run the tests
        success, output = self.run_command(
            ["poetry", "run", "pytest", "tests/", "-v", "--tb=short"],
            timeout=60
        )
        
        if success:
            # Count passed tests
            lines = output.split('\n')
            test_lines = [line for line in lines if '::' in line and ('PASSED' in line or 'FAILED' in line)]
            passed_count = len([line for line in test_lines if 'PASSED' in line])
            total_count = len(test_lines)
            
            self.print_result(
                "Unit Tests",
                success,
                f"{passed_count}/{total_count} tests passed"
            )
        else:
            self.print_result(
                "Unit Tests",
                False,
                f"Tests failed: {output[-200:]}"
            )
    
    def check_qodo_command(self) -> None:
        """Check if Qodo command is available."""
        self.print_header("Qodo Command Check")
        
        success, output = self.run_command(["qodo", "--version"])
        
        if success:
            self.print_result("Qodo Command", True, f"Available: {output.strip()}")
        else:
            self.print_result(
                "Qodo Command",
                False,
                "Not found. Install from https://docs.qodo.ai/installation"
            )
    
    def check_agent_configuration(self) -> None:
        """Verify agent configuration file is valid."""
        self.print_header("Agent Configuration Check")
        
        agent_config_path = self.project_root / "agents" / "sum_agent.toml"
        
        if not agent_config_path.exists():
            self.print_result("Agent Config File", False, "sum_agent.toml not found")
            return
        
        self.print_result("Agent Config File", True, "sum_agent.toml found")
        
        # Try to parse TOML
        try:
            import tomllib
            with open(agent_config_path, 'rb') as f:
                config = tomllib.load(f)
            
            # Check required sections for the new TOML structure
            required_sections = ['commands', 'commands.keyword_analysis_agent']
            
            for section in required_sections:
                keys = section.split('.')
                current = config
                
                for key in keys:
                    if key in current:
                        current = current[key]
                    else:
                        self.print_result(f"Config Section: {section}", False, "Missing")
                        break
                else:
                    self.print_result(f"Config Section: {section}", True, "Present")
            
            # Check for required fields in the command
            if 'commands' in config and 'keyword_analysis_agent' in config['commands']:
                command_config = config['commands']['keyword_analysis_agent']
                
                required_fields = ['description', 'instructions']
                for field in required_fields:
                    if field in command_config:
                        self.print_result(f"Command Field: {field}", True, "Present")
                    else:
                        self.print_result(f"Command Field: {field}", False, "Missing")
            
            # Check for top-level fields
            top_level_fields = ['version', 'execution_strategy']
            for field in top_level_fields:
                if field in config:
                    self.print_result(f"Top-level Field: {field}", True, "Present")
                else:
                    self.print_result(f"Top-level Field: {field}", False, "Missing")
                    
        except ImportError:
            # Fallback for Python < 3.11
            try:
                import toml
                with open(agent_config_path, 'r') as f:
                    config = toml.load(f)
                self.print_result("TOML Parsing", True, "Configuration valid")
            except ImportError:
                self.print_result("TOML Parsing", False, "toml library not available")
            except Exception as e:
                self.print_result("TOML Parsing", False, f"Parse error: {str(e)}")
        except Exception as e:
            self.print_result("TOML Parsing", False, f"Parse error: {str(e)}")
    
    def generate_summary(self) -> None:
        """Generate and display verification summary."""
        self.print_header("Verification Summary")
        
        total_tests = len(self.results)
        passed_tests = sum(1 for _, success, _ in self.results if success)
        failed_tests = total_tests - passed_tests
        
        print(f"{Colors.BOLD}Total Tests: {total_tests}{Colors.END}")
        print(f"{Colors.GREEN}Passed: {passed_tests}{Colors.END}")
        print(f"{Colors.RED}Failed: {failed_tests}{Colors.END}")
        
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        print(f"{Colors.BOLD}Success Rate: {success_rate:.1f}%{Colors.END}")
        
        if failed_tests > 0:
            print(f"\n{Colors.RED}{Colors.BOLD}Issues Found:{Colors.END}")
            for i, error in enumerate(self.errors, 1):
                print(f"{Colors.RED}{i}. {error}{Colors.END}")
            
            print(f"\n{Colors.YELLOW}{Colors.BOLD}Next Steps:{Colors.END}")
            print(f"{Colors.YELLOW}1. Review the failed checks above{Colors.END}")
            print(f"{Colors.YELLOW}2. Install missing dependencies{Colors.END}")
            print(f"{Colors.YELLOW}3. Fix configuration issues{Colors.END}")
            print(f"{Colors.YELLOW}4. Re-run this verification script{Colors.END}")
        else:
            print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 All checks passed! Workshop setup is complete.{Colors.END}")
            print(f"\n{Colors.CYAN}{Colors.BOLD}You can now proceed with the workshop:{Colors.END}")
            print(f"{Colors.CYAN}1. Start the MCP server: poetry run workshop-mcp-server{Colors.END}")
            print(f"{Colors.CYAN}2. Run tests: poetry run pytest{Colors.END}")
            print(f"{Colors.CYAN}3. Use the agent: qodo agent run agents/sum_agent.toml{Colors.END}")
    
    def run_all_checks(self) -> bool:
        """Run all verification checks."""
        print(f"{Colors.BOLD}{Colors.MAGENTA}")
        print("🔧 Workshop MCP Verification Script")
        print("===================================")
        print(f"{Colors.END}")
        
        # Run all checks
        self.check_python_version()
        self.check_poetry_installation()
        self.check_project_structure()
        self.check_dependencies()
        self.check_mcp_server_startup()
        self.check_keyword_search_functionality()
        self.run_unit_tests()
        self.check_qodo_command()
        self.check_agent_configuration()
        
        # Generate summary
        self.generate_summary()
        
        # Return overall success
        return len(self.errors) == 0


def main() -> None:
    """Main entry point for the verification script."""
    verifier = WorkshopVerifier()
    success = verifier.run_all_checks()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()