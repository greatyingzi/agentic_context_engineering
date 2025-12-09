#!/usr/bin/env python3
"""
Global exception handler for Agentic Context Engineering hooks.
Provides centralized error logging and reporting.
"""

import json
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict


class GlobalExceptionHandler:
    """Centralized exception handler for all hook operations."""

    def __init__(self):
        self.install_dir = Path.home() / ".claude"
        self.log_dir = self.install_dir / "logs"
        self.log_file = self.log_dir / "exceptions.log"
        self._ensure_log_directory()

    def _ensure_log_directory(self):
        """Ensure log directory exists."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def log_exception(self,
                     exception: Exception,
                     hook_name: str = "unknown",
                     context: Optional[Dict[str, Any]] = None,
                     session_id: Optional[str] = None) -> str:
        """
        Log an exception with full context to the global log file.

        Args:
            exception: The exception that occurred
            hook_name: Name of the hook where exception occurred
            context: Additional context data (input data, etc.)
            session_id: Session identifier if available

        Returns:
            Log entry ID for reference
        """
        timestamp = datetime.now().isoformat()
        exc_type = type(exception).__name__
        exc_msg = str(exception)
        exc_traceback = traceback.format_exc()

        # Generate unique log ID
        log_id = f"{timestamp.replace(':', '').replace('-', '')}_{hook_name}"

        # Prepare log entry
        log_entry = {
            "log_id": log_id,
            "timestamp": timestamp,
            "hook_name": hook_name,
            "session_id": session_id,
            "exception_type": exc_type,
            "exception_message": exc_msg,
            "traceback": exc_traceback,
            "context": context or {},
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }

        # Write to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, indent=2, ensure_ascii=False) + "\n")
                f.write("-" * 80 + "\n")
        except Exception as e:
            # Fallback to stderr if logging fails
            print(f"CRITICAL: Failed to write to exception log: {e}", file=sys.stderr)
            print(f"Original exception: {exception}", file=sys.stderr)

        return log_id

    def handle_and_exit(self,
                      exception: Exception,
                      hook_name: str = "unknown",
                      context: Optional[Dict[str, Any]] = None,
                      session_id: Optional[str] = None,
                      exit_code: int = 1):
        """
        Handle exception, log it, and exit gracefully.

        Args:
            exception: The exception that occurred
            hook_name: Name of the hook where exception occurred
            context: Additional context data
            session_id: Session identifier
            exit_code: Exit code for the process
        """
        log_id = self.log_exception(exception, hook_name, context, session_id)

        # Print user-friendly error message to stderr
        print(f"❌ Hook execution failed in {hook_name}", file=sys.stderr)
        print(f"📝 Error logged with ID: {log_id}", file=sys.stderr)
        print(f"📂 Check logs at: {self.log_file}", file=sys.stderr)

        # In diagnostic mode, also print full traceback
        diagnostic_flag = self.install_dir / "diagnostic_mode"
        if diagnostic_flag.exists():
            print(f"\n🐛 Full exception details:\n{traceback.format_exc()}", file=sys.stderr)

        sys.exit(exit_code)

    def handle_with_fallback(self,
                           exception: Exception,
                           hook_name: str = "unknown",
                           context: Optional[Dict[str, Any]] = None,
                           session_id: Optional[str] = None,
                           fallback_output: Optional[str] = None):
        """
        Handle exception but don't exit - return fallback output instead.

        Args:
            exception: The exception that occurred
            hook_name: Name of the hook where exception occurred
            context: Additional context data
            session_id: Session identifier
            fallback_output: JSON string to output as fallback

        Returns:
            Fallback output to return to Claude
        """
        log_id = self.log_exception(exception, hook_name, context, session_id)

        # Print warning to stderr
        print(f"⚠️  Hook {hook_name} encountered an error but continuing", file=sys.stderr)
        print(f"📝 Error logged with ID: {log_id}", file=sys.stderr)

        # Return fallback output (empty JSON by default)
        return fallback_output or "{}"


# Global instance for easy access
_global_handler = None

def get_exception_handler() -> GlobalExceptionHandler:
    """Get the global exception handler instance."""
    global _global_handler
    if _global_handler is None:
        _global_handler = GlobalExceptionHandler()
    return _global_handler


def hook_exception_wrapper(hook_name: str):
    """
    Decorator to wrap hook main functions with global exception handling.

    Args:
        hook_name: Name of the hook for logging purposes

    Usage:
        @hook_exception_wrapper("user_prompt_inject")
        def main():
            # Hook logic here
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            handler = get_exception_handler()
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Try to extract context from function arguments
                context = {}
                session_id = None

                # If first argument is the input data (common pattern)
                if args and hasattr(args[0], 'get'):
                    context = {"input_data": args[0]}
                    session_id = args[0].get('session_id')

                handler.handle_and_exit(e, hook_name, context, session_id)

        return wrapper
    return decorator


def log_hook_error(hook_name: str,
                  exception: Exception,
                  context: Optional[Dict[str, Any]] = None,
                  session_id: Optional[str] = None) -> str:
    """
    Convenience function to log hook errors without exiting.

    Args:
        hook_name: Name of the hook
        exception: Exception that occurred
        context: Additional context
        session_id: Session ID

    Returns:
        Log entry ID
    """
    handler = get_exception_handler()
    return handler.log_exception(exception, hook_name, context, session_id)


def get_log_file_path() -> Path:
    """Get the path to the global exception log file."""
    return get_exception_handler().log_file


def cleanup_old_logs(keep_days: int = 30):
    """
    Clean up old exception log entries (rotate logs).

    Args:
        keep_days: Number of days to keep log entries
    """
    handler = get_exception_handler()
    if not handler.log_file.exists():
        return

    cutoff_date = datetime.now().timestamp() - (keep_days * 24 * 60 * 60)

    # Read current log entries
    current_entries = []
    try:
        with open(handler.log_file, "r", encoding="utf-8") as f:
            content = f.read()
            entries = content.split("-" * 80)

            for entry in entries:
                if entry.strip():
                    try:
                        entry_data = json.loads(entry.strip())
                        entry_timestamp = datetime.fromisoformat(entry_data["timestamp"]).timestamp()
                        if entry_timestamp > cutoff_date:
                            current_entries.append(entry)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        # Keep malformed entries just in case
                        current_entries.append(entry)
    except Exception as e:
        print(f"Failed to clean up old logs: {e}", file=sys.stderr)
        return

    # Write back filtered entries
    try:
        with open(handler.log_file, "w", encoding="utf-8") as f:
            for entry in current_entries:
                if entry.strip():
                    f.write(entry.strip() + "\n")
                    f.write("-" * 80 + "\n")
    except Exception as e:
        print(f"Failed to write cleaned logs: {e}", file=sys.stderr)