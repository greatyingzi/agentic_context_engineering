#!/usr/bin/env python3
"""
Quick Cross-Platform Compatibility Checker

A lightweight script for quick cross-platform compatibility checks.
This is a simplified version for rapid validation.
"""

import os
import sys
import platform
import json
from pathlib import Path

def check_python_compatibility():
    """Check Python version and availability."""
    print("🐍 Checking Python compatibility...")

    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"❌ Python {version.major}.{version.minor} found. Requires Python 3.9+")
        return False

    print(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")

    # Test Python executable
    try:
        result = os.system(f"{sys.executable} --version > /dev/null 2>&1")
        if result == 0:
            print("✅ Python executable accessible - OK")
            return True
        else:
            print("❌ Python executable not accessible")
            return False
    except:
        print("❌ Error checking Python executable")
        return False

def check_node_compatibility():
    """Check Node.js and npm availability."""
    print("\n📦 Checking Node.js compatibility...")

    try:
        # Check node
        result = os.system("node --version > /dev/null 2>&1")
        if result == 0:
            print("✅ Node.js available - OK")
        else:
            print("❌ Node.js not found")
            return False

        # Check npm
        result = os.system("npm --version > /dev/null 2>&1")
        if result == 0:
            print("✅ npm available - OK")
            return True
        else:
            print("❌ npm not found")
            return False
    except:
        print("❌ Error checking Node.js")
        return False

def check_path_handling():
    """Check path handling for current platform."""
    print(f"\n🛣️  Checking path handling for {platform.system()}...")

    current_platform = platform.system().lower()

    # Test path joining
    test_paths = [".claude", "hooks", "test_script.py"]
    if current_platform == "windows":
        expected_sep = "\\"
    else:
        expected_sep = "/"

    joined_path = os.path.join(*test_paths)
    if expected_sep in joined_path:
        print(f"✅ Path separator correct: {expected_sep}")
    else:
        print(f"❌ Path separator issue: {joined_path}")
        return False

    # Test home directory expansion
    home = Path.home()
    if home.exists():
        print(f"✅ Home directory accessible: {home}")
    else:
        print("❌ Home directory not accessible")
        return False

    # Test .claude directory
    claude_dir = home / ".claude"
    print(f"ℹ Claude directory: {claude_dir}")

    return True

def check_command_generation():
    """Check command generation for current platform."""
    print(f"\n⚡ Checking command generation for {platform.system()}...")

    current_platform = platform.system().lower()

    # Test Python command
    if current_platform == "windows":
        python_cmd = "python"
        pip_cmd = "python -m pip"
    else:
        python_cmd = "python3"
        pip_cmd = "python3 -m pip"

    # Test command execution
    try:
        result = os.system(f"{python_cmd} --version > /dev/null 2>&1")
        if result == 0:
            print(f"✅ {python_cmd} command works")
        else:
            print(f"❌ {python_cmd} command fails")
            return False

        result = os.system(f"{pip_cmd} --version > /dev/null 2>&1")
        if result == 0:
            print(f"✅ {pip_cmd} command works")
            return True
        else:
            print(f"❌ {pip_cmd} command fails")
            return False
    except:
        print("❌ Error testing commands")
        return False

def check_installation_files():
    """Check if installation files exist."""
    print("\n📁 Checking installation files...")

    required_files = [
        "install.js",
        "package.json",
        "src/hooks",
        "src/hooks/common.py",
        "src/hooks/utils",
        "src/hooks/utils/path_utils.py",
        "src/prompts"
    ]

    all_exist = True
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            all_exist = False

    return all_exist

def simulate_windows_commands():
    """Simulate Windows command generation."""
    print("\n🪟 Simulating Windows commands...")

    # Simulate Windows paths
    windows_paths = [
        ("C:\\Users\\testuser\\.claude\\.venv\\Scripts\\python.exe", "C:\\Users\\testuser\\.claude\\hooks\\session_end.py"),
        ("C:\\Program Files\\Python39\\python.exe", "C:\\Users\\testuser\\project\\script.py")
    ]

    for venv_python, script_path in windows_paths:
        # Windows command format
        command = f'"{venv_python}" "{script_path}"'
        print(f"✅ Windows command: {command}")

        # Check for proper quoting
        if command.count('"') == 4 and venv_python in command and script_path in command:
            print("  ✅ Command format correct")
        else:
            print("  ❌ Command format issue")
            return False

    return True

def generate_quick_report():
    """Generate a quick compatibility report."""
    print("\n📊 Generating quick report...")

    report = {
        "timestamp": str(Path.home()),
        "platform": {
            "system": platform.system(),
            "version": platform.version(),
            "machine": platform.machine()
        },
        "python": {
            "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "executable": sys.executable,
            "path": sys.path
        },
        "environment": {
            "home": str(Path.home()),
            "path": os.environ.get("PATH", ""),
            "claude_dir": str(Path.home() / ".claude")
        }
    }

    # Save report
    report_path = Path("quick_compatibility_report.json")
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"✅ Report saved to: {report_path}")
    return report

def main():
    """Run quick compatibility checks."""
    print("🔧 Quick Cross-Platform Compatibility Checker")
    print("=" * 50)

    results = []

    # Run checks
    results.append(("Python Compatibility", check_python_compatibility()))
    results.append(("Node.js Compatibility", check_node_compatibility()))
    results.append(("Path Handling", check_path_handling()))
    results.append(("Command Generation", check_command_generation()))
    results.append(("Installation Files", check_installation_files()))

    # Windows simulation
    if platform.system().lower() != "windows":
        results.append(("Windows Command Simulation", simulate_windows_commands()))

    # Generate report
    generate_quick_report()

    # Summary
    print("\n" + "=" * 50)
    print("🎯 Quick Check Summary:")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for check, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {check}: {status}")

    print(f"\nOverall: {passed}/{total} checks passed")

    if passed == total:
        print("🎉 All checks passed! System appears compatible.")
        return 0
    else:
        print("⚠️  Some checks failed. Review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())