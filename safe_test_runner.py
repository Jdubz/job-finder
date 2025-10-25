#!/usr/bin/env python3

"""
Safe Test Runner - job-finder-worker

Prevents test explosions through process locking and resource control.
This is the ONLY way to run tests in this repository.
"""

import json
import os
import signal
import subprocess
import sys
import threading
import time

import psutil

# Configuration
LOCK_FILE = ".test-lock"
MAX_MEMORY_MB = 2048  # 2GB max memory
MAX_EXECUTION_TIME = 600  # 10 minutes
STALE_LOCK_THRESHOLD = 900  # 15 minutes


class SafeTestRunner:
    """
    Manages safe test execution by enforcing process locking, resource limits,
    and test termination. Ensures that only one test process runs at a time,
    monitors memory and execution time, and handles cleanup of stale or
    corrupted lock files.
    """

    def __init__(self):
        self.start_time = time.time()
        self.lock_acquired = False
        self.stop_monitoring = threading.Event()
        self.last_log_time = 0

    def acquire_lock(self):
        """Acquire exclusive test execution lock with atomic file creation."""
        if os.path.exists(LOCK_FILE):
            try:
                with open(LOCK_FILE, "r") as f:
                    lock_data = json.load(f)
                lock_age = time.time() - lock_data["start_time"]

                # If lock is older than STALE_LOCK_THRESHOLD, consider it stale
                if lock_age > STALE_LOCK_THRESHOLD:
                    print("⚠️  Removing stale lock file")
                    os.unlink(LOCK_FILE)
                else:
                    print("❌ Another test process is already running")
                    print(f"   PID: {lock_data['pid']}")
                    print(f"   Started: {lock_data['start_time']}")
                    sys.exit(1)
            except (json.JSONDecodeError, KeyError):
                # Corrupted lock file, remove it
                os.unlink(LOCK_FILE)

        # Create lock file atomically using os.open with O_CREAT|O_EXCL
        # This ensures atomic creation without race conditions
        lock_data = {
            "pid": os.getpid(),
            "start_time": time.time(),
            "repository": "job-finder-worker",
            "test_suite": "unit",
        }

        try:
            # Atomic lock file creation
            fd = os.open(LOCK_FILE, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
            try:
                os.write(fd, json.dumps(lock_data).encode())
            finally:
                os.close(fd)
        except FileExistsError:
            # Another process acquired the lock between our check and creation
            print("❌ Another test process acquired the lock concurrently")
            sys.exit(1)

        self.lock_acquired = True
        print("🔒 Test execution lock acquired")

    def release_lock(self):
        """Release test execution lock."""
        if self.lock_acquired and os.path.exists(LOCK_FILE):
            os.unlink(LOCK_FILE)
            print("🔓 Test execution lock released")

    def monitor_resources(self):
        """
        Monitor system resources during test execution.
        Monitors both main process and all child processes (pytest workers).
        """
        try:
            while not self.stop_monitoring.is_set():
                try:
                    # Check memory usage (including all child processes)
                    process = psutil.Process()
                    memory_mb = process.memory_info().rss / 1024 / 1024

                    # Add memory usage of all child processes recursively
                    for child in process.children(recursive=True):
                        try:
                            memory_mb += child.memory_info().rss / 1024 / 1024
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass

                    if memory_mb > MAX_MEMORY_MB:
                        print(f"\n⚠️  CRITICAL: Memory usage exceeded {MAX_MEMORY_MB}MB")
                        print(f"Current usage: {round(memory_mb, 1)}MB")
                        self.terminate_tests()
                        sys.exit(1)

                    # Check execution time
                    execution_time = time.time() - self.start_time
                    if execution_time > MAX_EXECUTION_TIME:
                        print(f"\n⚠️  CRITICAL: Test execution exceeded {MAX_EXECUTION_TIME}s")
                        self.terminate_tests()
                        sys.exit(1)

                    # Log status every 30 seconds (using explicit time tracking)
                    if execution_time - self.last_log_time >= 30:
                        print(
                            f"[Monitor] Memory: {round(memory_mb, 1)}MB | Time: {round(execution_time, 1)}s"
                        )
                        self.last_log_time = execution_time

                    time.sleep(1)
                except KeyboardInterrupt:
                    break
        finally:
            # Ensure lock is released when monitor thread exits
            self.release_lock()

    def terminate_tests(self):
        """Terminate all test processes."""
        print("\n🛑 Terminating test processes...")
        try:
            # Kill pytest processes
            for proc in psutil.process_iter(["pid", "name", "cmdline"]):
                try:
                    if "pytest" in " ".join(proc.info["cmdline"] or []):
                        proc.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"Error terminating processes: {e}")

    def run_tests(self):
        """Run tests with safety controls."""
        print("\n🧪 Running tests...")

        try:
            # Run pytest with timeout, using sys.executable for consistency
            result = subprocess.run(
                [sys.executable, "-m", "pytest"],
                timeout=MAX_EXECUTION_TIME,
                capture_output=False,
            )

            if result.returncode == 0:
                print("✅ Tests completed successfully")
                return True
            else:
                print(f"❌ Tests failed (exit code: {result.returncode})")
                return False

        except subprocess.TimeoutExpired:
            print(f"❌ Tests timed out after {MAX_EXECUTION_TIME}s")
            return False
        except Exception as e:
            print(f"❌ Error running tests: {e}")
            return False

    def run(self):
        """Main execution entry point."""
        print("\n🛡️  Safe Test Runner - job-finder-worker\n")

        try:
            # Acquire lock
            self.acquire_lock()

            # Start monitoring in background
            monitor_thread = threading.Thread(target=self.monitor_resources)
            monitor_thread.daemon = True
            monitor_thread.start()

            # Run tests
            success = self.run_tests()

            # Stop monitoring and cleanup
            self.stop_monitoring.set()
            self.release_lock()

            # Exit with appropriate code
            sys.exit(0 if success else 1)

        except KeyboardInterrupt:
            print("\n\nReceived interrupt signal, cleaning up...")
            self.stop_monitoring.set()
            self.terminate_tests()
            self.release_lock()
            sys.exit(130)
        except Exception as e:
            print(f"Fatal error: {e}")
            self.stop_monitoring.set()
            self.release_lock()
            sys.exit(1)


if __name__ == "__main__":
    runner = SafeTestRunner()
    runner.run()
