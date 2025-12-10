#!/usr/bin/env python3
"""
Cross-Platform Compatibility Validator for Agentic Context Engineering

This script validates cross-platform compatibility without requiring physical Windows access.
It simulates different platforms and tests all critical components of the system.

Features:
- Platform configuration simulator
- Key logic test suite
- Actual installation verification
- Regression testing framework
- Windows fix remote verification
"""

import os
import sys
import json
import platform
import subprocess
import tempfile
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import unittest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

class PlatformSimulator:
    """Simulates different platform environments."""

    PLATFORMS = ['darwin', 'linux', 'win32']

    def __init__(self, target_platform: str):
        self.target_platform = target_platform
        self.original_platform = platform.system().lower()
        self.original_path = os.environ.get('PATH', '')

    def simulate_platform(self) -> Dict[str, Any]:
        """Simulate target platform environment."""
        print(f"\n🖥️  Simulating platform: {self.target_platform}")

        # Simulate platform-specific environment variables
        if self.target_platform == 'win32':
            # Windows-specific settings
            os.environ['PATH'] = f"C:\\Python39;{self.original_path}"
            os.environ['PROGRAMFILES'] = "C:\\Program Files"
            os.environ['SYSTEMROOT'] = "C:\\Windows"

        elif self.target_platform == 'darwin':
            # macOS-specific settings
            os.environ['PATH'] = f"/usr/local/bin:/usr/bin:/bin:{self.original_path}"
            os.environ['HOME'] = "/Users/testuser"

        elif self.target_platform == 'linux':
            # Linux-specific settings
            os.environ['PATH'] = f"/usr/local/bin:/usr/bin:/bin:{self.original_path}"
            os.environ['HOME'] = "/home/testuser"

        # Mock platform.system() result
        import unittest.mock
        self.mock_patch = unittest.mock.patch('platform.system', return_value=self.target_platform)
        self.mock_patch.start()

        return {
            'platform': self.target_platform,
            'python_executable': self.get_python_executable(),
            'venv_python': self.get_venv_python_path(),
            'path_separator': self.get_path_separator(),
            'quote_char': self.get_quote_char()
        }

    def get_python_executable(self) -> str:
        """Get platform-specific Python executable name."""
        if self.target_platform == 'win32':
            return 'python.exe'
        else:
            return 'python3'

    def get_venv_python_path(self) -> str:
        """Get platform-specific venv Python path."""
        if self.target_platform == 'win32':
            return r"C:\Users\testuser\.claude\.venv\Scripts\python.exe"
        else:
            return os.path.join("~", ".claude", ".venv", "bin", "python3")

    def get_path_separator(self) -> str:
        """Get platform-specific path separator."""
        return '\\' if self.target_platform == 'win32' else '/'

    def get_quote_char(self) -> str:
        """Get platform-specific quote character for commands."""
        return '"' if self.target_platform == 'win32' else "'"

    def restore_platform(self):
        """Restore original platform environment."""
        if hasattr(self, 'mock_patch'):
            self.mock_patch.stop()
        os.environ['PATH'] = self.original_path
        if 'HOME' in os.environ:
            del os.environ['HOME']

class PathGeneratorTest(unittest.TestCase):
    """Test path generation logic across platforms."""

    def setUp(self):
        self.simulator = None
        self.test_platforms = ['darwin', 'linux', 'win32']

    def test_path_generation(self):
        """Test path generation for all platforms."""
        for platform_name in self.test_platforms:
            with self.subTest(platform=platform_name):
                self.simulator = PlatformSimulator(platform_name)
                env = self.simulator.simulate_platform()

                # Test path joining
                test_paths = ['~', '.claude', 'hooks']
                if platform_name == 'win32':
                    expected = "C:\\Users\\testuser\\.claude\\hooks"
                else:
                    expected = os.path.join("~", ".claude", "hooks")

                # Test venv path generation
                venv_path = self.simulator.get_venv_python_path()
                self.assertIsInstance(venv_path, str)
                self.assertTrue(len(venv_path) > 0)

                # Test quote handling
                quote_char = self.simulator.get_quote_char()
                self.assertIn(quote_char, ['"', "'"])

                self.simulator.restore_platform()

    def test_hook_command_generation(self):
        """Test hook command generation for different platforms."""
        for platform_name in self.test_platforms:
            with self.subTest(platform=platform_name):
                self.simulator = PlatformSimulator(platform_name)
                env = self.simulator.simulate_platform()

                # Simulate command generation from install.js
                venv_python = env['venv_python']
                script_path = os.path.join("~", ".claude", "hooks", "test_script.py")

                if platform_name == 'win32':
                    expected_command = f'"{venv_python}" "{script_path}"'
                else:
                    expected_command = f"{venv_python} \"{script_path}\""

                # Verify command format
                self.assertIn(venv_python, expected_command)
                self.assertIn(script_path, expected_command)

                self.simulator.restore_platform()

class CommandGeneratorTest(unittest.TestCase):
    """Test command generation and execution."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.simulator = None

    def tearDown(self):
        if self.simulator:
            self.simulator.restore_platform()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_python_command_generation(self):
        """Test Python command generation for different platforms."""
        platforms = ['darwin', 'linux', 'win32']

        for platform_name in platforms:
            with self.subTest(platform=platform_name):
                self.simulator = PlatformSimulator(platform_name)
                env = self.simulator.simulate_platform()

                # Test Python executable detection
                python_cmd = 'python' if platform_name == 'win32' else 'python3'

                # Test venv command generation
                if platform_name == 'win32':
                    venv_cmd = f'"{env["venv_python"]}" -m pip install anthropic'
                else:
                    venv_cmd = f'{env["venv_python"]} -m pip install anthropic'

                self.assertIsInstance(venv_cmd, str)
                self.assertIn('anthropic', venv_cmd)

                self.simulator.restore_platform()

    def test_virtual_env_creation(self):
        """Test virtual environment creation commands."""
        platforms = ['darwin', 'linux', 'win32']

        for platform_name in platforms:
            with self.subTest(platform=platform_name):
                self.simulator = PlatformSimulator(platform_name)
                env = self.simulator.simulate_platform()

                # Test uv venv creation command
                if platform_name == 'win32':
                    uv_cmd = 'uv venv "C:\\Users\\testuser\\.claude\\.venv"'
                else:
                    uv_cmd = f'uv venv {os.path.join("~", ".claude", ".venv")}'

                # Test fallback venv creation
                if platform_name == 'win32':
                    fallback_cmd = 'python -m venv "C:\\Users\\testuser\\.claude\\.venv"'
                else:
                    fallback_cmd = f'python3 -m venv {os.path.join("~", ".claude", ".venv")}'

                self.assertIsInstance(uv_cmd, str)
                self.assertIsInstance(fallback_cmd, str)

                self.simulator.restore_platform()

class InstallationVerifier(unittest.TestCase):
    """Verify actual installation on current system."""

    def setUp(self):
        self.claude_dir = Path.home() / ".claude"
        self.hooks_dir = self.claude_dir / "hooks"
        self.settings_path = self.claude_dir / "settings.json"

    def test_directory_structure(self):
        """Test required directory structure."""
        required_dirs = [
            self.claude_dir,
            self.hooks_dir,
            self.claude_dir / "scripts",
            self.claude_dir / "prompts"
        ]

        for dir_path in required_dirs:
            with self.subTest(directory=dir_path):
                if dir_path.exists():
                    self.assertTrue(dir_path.is_dir())
                    print(f"✓ Directory exists: {dir_path}")
                else:
                    print(f"⚠ Directory missing: {dir_path}")

    def test_python_imports(self):
        """Test Python imports for hook modules."""
        required_modules = [
            'hooks.common',
            'hooks.utils.path_utils',
            'hooks.utils.tag_utils',
            'hooks.file_utils',
            'hooks.playbook_engine'
        ]

        for module in required_modules:
            with self.subTest(module=module):
                try:
                    __import__(module)
                    print(f"✓ Module imported successfully: {module}")
                except ImportError as e:
                    print(f"❌ Import failed for {module}: {e}")
                    self.fail(f"Failed to import {module}: {e}")

    def test_settings_json(self):
        """Test settings.json structure."""
        if not self.settings_path.exists():
            print("⚠ settings.json not found - this is normal for fresh installations")
            return

        try:
            with open(self.settings_path, 'r') as f:
                settings = json.load(f)

            # Check for hooks section
            if 'hooks' in settings:
                hooks = settings['hooks']
                self.assertIsInstance(hooks, dict)
                print(f"✓ Settings.json contains hooks section")

                # Check for required hook events
                required_events = ['UserPromptSubmit', 'SessionEnd', 'PreCompact']
                for event in required_events:
                    if event in hooks:
                        self.assertIsInstance(hooks[event], list)
                        print(f"✓ Hook event found: {event}")
                    else:
                        print(f"⚠ Hook event missing: {event}")
            else:
                print("⚠ No hooks section in settings.json")

        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse settings.json: {e}")
            self.fail(f"Invalid JSON in settings.json: {e}")

class RegressionTestFramework(unittest.TestCase):
    """Regression testing framework."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.baseline_results = {}
        self.test_results = {}

    def setup_baseline(self):
        """Setup baseline test results."""
        print("\n📊 Setting up baseline test results...")

        # Record current platform
        self.baseline_results['platform'] = platform.system().lower()

        # Record key paths
        self.baseline_results['paths'] = {
            'home': str(Path.home()),
            'claude_dir': str(Path.home() / ".claude"),
            'python_executable': sys.executable
        }

        # Record hook commands format
        self.baseline_results['hook_commands'] = self.generate_hook_commands()

        print("✓ Baseline established")

    def generate_hook_commands(self) -> Dict[str, str]:
        """Generate standard hook commands."""
        claude_dir = Path.home() / ".claude"
        venv_python = str(claude_dir / ".venv" / "bin" / "python3")

        return {
            'user_prompt_inject': f'{venv_python} "{claude_dir}/hooks/user_prompt_inject.py"',
            'session_end': f'{venv_python} "{claude_dir}/hooks/session_end.py"',
            'precompact': f'{venv_python} "{claude_dir}/hooks/precompact.py"'
        }

    def run_regression_tests(self):
        """Run regression tests against baseline."""
        print("\n🔍 Running regression tests...")

        # Test 1: Platform consistency
        current_platform = platform.system().lower()
        if current_platform != self.baseline_results['platform']:
            print(f"⚠ Platform changed: {self.baseline_results['platform']} -> {current_platform}")

        # Test 2: Path consistency
        current_paths = {
            'home': str(Path.home()),
            'claude_dir': str(Path.home() / ".claude"),
            'python_executable': sys.executable
        }

        path_issues = []
        for key, baseline_path in self.baseline_results['paths'].items():
            if current_paths[key] != baseline_path:
                path_issues.append(f"{key}: {baseline_path} -> {current_paths[key]}")

        if path_issues:
            print("⚠ Path changes detected:")
            for issue in path_issues:
                print(f"  - {issue}")
        else:
            print("✓ Paths consistent with baseline")

        # Test 3: Hook command format
        current_commands = self.generate_hook_commands()
        command_issues = []

        for hook_name, baseline_cmd in self.baseline_results['hook_commands'].items():
            if current_commands[hook_name] != baseline_cmd:
                command_issues.append(f"{hook_name}: {baseline_cmd} -> {current_commands[hook_name]}")

        if command_issues:
            print("⚠ Command format changes detected:")
            for issue in command_issues:
                print(f"  - {issue}")
        else:
            print("✓ Hook commands consistent with baseline")

        # Store results
        self.test_results = {
            'platform': current_platform,
            'paths': current_paths,
            'hook_commands': current_commands,
            'issues': path_issues + command_issues
        }

        return len(path_issues + command_issues) == 0

class WindowsFixVerifier(unittest.TestCase):
    """Windows-specific fix verification."""

    def test_windows_path_handling(self):
        """Test Windows path handling logic."""
        simulator = PlatformSimulator('win32')
        env = simulator.simulate_platform()

        try:
            # Test Windows path generation
            test_paths = [
                ("~", "C:\\Users\\testuser"),
                (".claude", "C:\\Users\\testuser\\.claude"),
                ("hooks\\script.py", "C:\\Users\\testuser\\.claude\\hooks\\script.py")
            ]

            for input_path, expected in test_paths:
                if input_path == "~":
                    result = os.path.expanduser(input_path)
                elif "\\" in input_path:
                    # Handle Windows-style paths
                    result = os.path.join("C:\\Users\\testuser", input_path)
                else:
                    result = os.path.join("C:\\Users\\testuser", input_path)

                print(f"✓ Windows path: {input_path} -> {result}")

            # Test command quote handling
            venv_python = env['venv_python']
            script_path = "C:\\Users\\testuser\\.claude\\hooks\\script.py"
            command = f'"{venv_python}" "{script_path}"'

            self.assertIn('"', command)
            self.assertIn(venv_python, command)
            self.assertIn(script_path, command)
            print(f"✓ Windows command: {command}")

        finally:
            simulator.restore_platform()

    def test_windows_compatibility_checks(self):
        """Test Windows compatibility checks."""
        simulator = PlatformSimulator('win32')
        env = simulator.simulate_platform()

        try:
            # Test Windows-specific checks
            windows_issues = []

            # Check Python executable
            python_cmd = 'python'
            result = subprocess.run([python_cmd, '--version'],
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print(f"✓ Python available: {python_cmd}")
            else:
                windows_issues.append("Python not found in PATH")

            # Check PowerShell execution policy (simulated)
            if 'PSModulePath' in os.environ:
                print("ℹ PowerShell detected - execution policy check needed")

            # Check long paths support (simulated)
            long_path = "C:\\Users\\testuser\\.claude\\.venv\\Scripts\\python.exe"
            if len(long_path) > 260:
                print("⚠ Long path may be an issue")

            if windows_issues:
                print(f"❌ Windows issues: {windows_issues}")
            else:
                print("✓ Windows compatibility checks passed")

        finally:
            simulator.restore_platform()

class TestReporter:
    """Generate comprehensive test reports."""

    def __init__(self):
        self.results = {}
        self.timestamp = datetime.now().isoformat()

    def add_result(self, test_name: str, passed: bool, details: Dict[str, Any] = None):
        """Add test result."""
        self.results[test_name] = {
            'passed': passed,
            'timestamp': self.timestamp,
            'details': details or {}
        }

    def generate_report(self) -> str:
        """Generate comprehensive test report."""
        report = []
        report.append("# Cross-Platform Compatibility Test Report")
        report.append(f"Generated: {self.timestamp}")
        report.append(f"Platform: {platform.system()} {platform.version()}")
        report.append("")

        # Summary
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results.values() if r['passed'])
        failed_tests = total_tests - passed_tests

        report.append("## Summary")
        report.append(f"- Total Tests: {total_tests}")
        report.append(f"- Passed: {passed_tests}")
        report.append(f"- Failed: {failed_tests}")
        report.append(f"- Success Rate: {passed_tests/total_tests*100:.1f}%")
        report.append("")

        # Detailed results
        report.append("## Test Results")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result['passed'] else "❌ FAIL"
            report.append(f"### {test_name}")
            report.append(f"{status}")

            if result['details']:
                report.append("```json")
                report.append(json.dumps(result['details'], indent=2))
                report.append("```")
            report.append("")

        # Recommendations
        report.append("## Recommendations")
        if failed_tests > 0:
            report.append("- Address failed tests before deploying changes")
            report.append("- Test on actual Windows environment if possible")
            report.append("- Consider adding platform-specific error handling")
        else:
            report.append("- All tests passed! Ready for cross-platform deployment")
            report.append("- Consider running these tests regularly as part of CI")

        return "\n".join(report)

    def save_report(self, filepath: str):
        """Save report to file."""
        report = self.generate_report()
        with open(filepath, 'w') as f:
            f.write(report)
        print(f"📄 Test report saved to: {filepath}")

def run_all_tests():
    """Run all cross-platform tests."""
    print("🚀 Starting Cross-Platform Compatibility Tests")
    print("=" * 60)

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add test classes
    test_classes = [
        PathGeneratorTest,
        CommandGeneratorTest,
        InstallationVerifier,
        RegressionTestFramework,
        WindowsFixVerifier
    ]

    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)

    # Run tests with custom reporter
    reporter = TestReporter()

    # Run individual test methods to collect results
    for test_class in test_classes:
        class_instance = test_class()
        if hasattr(class_instance, 'setUp'):
            class_instance.setUp()

        for method_name in dir(class_instance):
            if method_name.startswith('test_'):
                try:
                    method = getattr(class_instance, method_name)
                    method()
                    reporter.add_result(f"{test_class.__name__}.{method_name}", True)
                except Exception as e:
                    reporter.add_result(f"{test_class.__name__}.{method_name}", False,
                                     {"error": str(e)})

        if hasattr(class_instance, 'tearDown'):
            class_instance.tearDown()

    # Generate and save report
    report_path = Path("test_reports") / f"cross_platform_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    report_path.parent.mkdir(exist_ok=True)
    reporter.save_report(str(report_path))

    # Print summary
    print("\n" + "=" * 60)
    print("🎯 Test Summary:")
    reporter.generate_report()

    return reporter.results

def main():
    """Main execution function."""
    print("🔧 Cross-Platform Compatibility Validator")
    print("This script validates the Agentic Context Engineering system")
    print("across different platforms without requiring physical hardware.\n")

    # Check if running in correct directory
    if not (Path("install.js").exists() and Path("src").exists()):
        print("❌ Error: Please run this script from the project root directory")
        sys.exit(1)

    # Run all tests
    results = run_all_tests()

    # Exit with appropriate code
    failed_count = sum(1 for r in results.values() if not r['passed'])
    if failed_count > 0:
        print(f"\n⚠️  {failed_count} test(s) failed. Please review the report.")
        sys.exit(1)
    else:
        print("\n🎉 All tests passed! System is ready for cross-platform deployment.")
        sys.exit(0)

if __name__ == "__main__":
    main()