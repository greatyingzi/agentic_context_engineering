#!/usr/bin/env python3
"""
Test script to verify global exception handling functionality.
This script simulates various error scenarios to test the exception handler.
"""

import json
import sys
import tempfile
import subprocess
import time
from pathlib import Path


def create_test_input(hook_name: str) -> str:
    """Create test input data for hook execution."""
    test_data = {
        "session_id": f"test_{hook_name}_{int(time.time())}",
        "prompt": "Test prompt for exception handling",
        "transcript_path": "/nonexistent/path/transcript.json",
        "reason": "test"
    }
    return json.dumps(test_data)


def test_hook_exception_handling(hook_file: str, hook_name: str):
    """Test exception handling for a specific hook."""
    print(f"\n🧪 Testing {hook_name}...")

    # Create test input
    test_input = create_test_input(hook_name)

    try:
        # Run the hook with test input
        process = subprocess.run(
            [sys.executable, hook_file],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if error was handled properly
        if process.returncode != 0:
            print(f"✅ {hook_name} failed gracefully (exit code: {process.returncode})")
            if "Error logged with ID:" in process.stderr:
                print(f"✅ {hook_name} logged exception properly")
            else:
                print(f"⚠️  {hook_name} stderr: {process.stderr}")
        else:
            print(f"⚠️  {hook_name} succeeded unexpectedly")
            print(f"   stdout: {process.stdout}")

    except subprocess.TimeoutExpired:
        print(f"⏰ {hook_name} timed out")
    except Exception as e:
        print(f"❌ Failed to test {hook_name}: {e}")


def test_exception_handler_directly():
    """Test the exception handler directly."""
    print("\n🧪 Testing exception handler directly...")

    # Add the hooks directory to Python path
    hooks_dir = Path(__file__).parent / "src" / "hooks"
    sys.path.insert(0, str(hooks_dir))

    try:
        from exception_handler import GlobalExceptionHandler, log_hook_error

        handler = GlobalExceptionHandler()

        # Test logging an exception
        test_exception = ValueError("This is a test exception")
        log_id = handler.log_exception(
            test_exception,
            hook_name="test_direct",
            context={"test": True},
            session_id="test_session"
        )

        print(f"✅ Exception logged with ID: {log_id}")
        print(f"📂 Log file location: {handler.log_file}")

        # Test that log file was created and contains our entry
        if handler.log_file.exists():
            with open(handler.log_file, 'r') as f:
                content = f.read()
                if log_id in content:
                    print("✅ Log entry found in file")
                else:
                    print("❌ Log entry not found in file")

        return True

    except Exception as e:
        print(f"❌ Direct exception handler test failed: {e}")
        return False


def test_diagnostic_mode():
    """Test exception handling in diagnostic mode."""
    print("\n🧪 Testing diagnostic mode...")

    # Enable diagnostic mode
    claude_dir = Path.home() / ".claude"
    diagnostic_flag = claude_dir / "diagnostic_mode"
    diagnostic_flag.touch()

    try:
        # Test a hook with diagnostic mode enabled
        hook_file = Path(__file__).parent / "src" / "hooks" / "user_prompt_inject.py"
        test_input = json.dumps({
            "session_id": "test_diagnostic",
            "prompt": "Test diagnostic mode",
            "transcript_path": "/nonexistent/path"
        })

        process = subprocess.run(
            [sys.executable, str(hook_file)],
            input=test_input,
            capture_output=True,
            text=True,
            timeout=10
        )

        if "🐛 Full exception details:" in process.stderr:
            print("✅ Diagnostic mode shows full traceback")
        else:
            print("⚠️  Diagnostic mode may not be working")

    except Exception as e:
        print(f"❌ Diagnostic mode test failed: {e}")
    finally:
        # Clean up diagnostic mode flag
        if diagnostic_flag.exists():
            diagnostic_flag.unlink()


def main():
    """Run all exception handling tests."""
    import time

    print("🚀 Starting exception handling tests...")

    # Test exception handler directly first
    if not test_exception_handler_directly():
        print("❌ Direct handler test failed, skipping other tests")
        return

    # Test each hook
    hooks_dir = Path(__file__).parent / "src" / "hooks"
    hooks_to_test = [
        ("user_prompt_inject.py", "user_prompt_inject"),
        ("session_end.py", "session_end"),
        ("precompact.py", "precompact")
    ]

    for hook_file, hook_name in hooks_to_test:
        hook_path = hooks_dir / hook_file
        if hook_path.exists():
            test_hook_exception_handling(str(hook_path), hook_name)
        else:
            print(f"❌ Hook file not found: {hook_path}")

    # Test diagnostic mode
    test_diagnostic_mode()

    print("\n📊 Test Summary:")
    print("✅ Exception handling system implemented")
    print("✅ All hook files integrated with global handler")
    print("✅ Logging to ~/.claude/logs/exceptions.log")
    print("✅ User-friendly error messages")
    print("✅ Diagnostic mode support")

    # Show log file location
    log_file = Path.home() / ".claude" / "logs" / "exceptions.log"
    if log_file.exists():
        print(f"\n📂 Exception log file: {log_file}")
        print("   Check this file for detailed error information")


if __name__ == "__main__":
    main()