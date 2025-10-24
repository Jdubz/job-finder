#!/usr/bin/env python3
"""
Local E2E Test Runner

Runs E2E tests against Firebase emulators running in the portfolio project.
This allows testing the complete job-finder pipeline locally without touching
staging or production data.

Prerequisites:
    1. job-finder-FE Firebase emulators must be running:
       cd ~/path/to/portfolio && make firebase-emulators

    2. Emulators should be accessible on:
       - Firestore: localhost:8080
       - Auth: localhost:9099
       - UI: localhost:4000

Usage:
    # Run fast E2E test (4 jobs)
    python tests/e2e/run_local_e2e.py

    # Run full E2E test (20+ jobs)
    python tests/e2e/run_local_e2e.py --full

    # Run with verbose logging
    python tests/e2e/run_local_e2e.py --verbose

    # Run without Docker (direct Python execution)
    python tests/e2e/run_local_e2e.py --no-docker

    # Custom emulator host
    python tests/e2e/run_local_e2e.py --emulator-host localhost:8080
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime


# Color codes for output
class Colors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    BLUE = "\033[34m"


def print_header(message: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 70}{Colors.RESET}\n")


def print_info(message: str) -> None:
    """Print an info message."""
    print(f"{Colors.BLUE}ℹ{Colors.RESET} {message}")


def print_success(message: str) -> None:
    """Print a success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_warning(message: str) -> None:
    """Print a warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {message}")


def print_error(message: str) -> None:
    """Print an error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def check_emulator_running(host: str = "localhost:8080") -> bool:
    """Check if Firebase emulator is running."""
    import socket

    try:
        host_parts = host.split(":")
        hostname = host_parts[0]
        port = int(host_parts[1]) if len(host_parts) > 1 else 8080

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((hostname, port))
        sock.close()
        return result == 0
    except Exception as e:
        print_error(f"Error checking emulator: {e}")
        return False


def check_docker_available() -> bool:
    """Check if Docker is available."""
    try:
        subprocess.run(["docker", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def run_with_docker(args: argparse.Namespace) -> int:
    """Run E2E test using Docker Compose."""
    print_header("Running Local E2E Test with Docker")

    # Generate test run ID
    test_run_id = f"e2e_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Prepare environment variables
    env = os.environ.copy()
    env["TEST_RUN_ID"] = test_run_id
    env["FIRESTORE_EMULATOR_HOST"] = args.emulator_host

    # Build docker-compose command
    cmd = [
        "docker",
        "compose",
        "-f",
        "docker-compose.local-e2e.yml",
        "up",
        "--build" if args.build else "--no-build",
        "--abort-on-container-exit",
        "--remove-orphans",
    ]

    print_info(f"Test Run ID: {test_run_id}")
    print_info(f"Emulator Host: {args.emulator_host}")
    print_info(f"Mode: {'Full' if args.full else 'Fast'}")
    print_info(f"Command: {' '.join(cmd)}")
    print()

    # Run docker-compose
    try:
        result = subprocess.run(cmd, env=env)

        if result.returncode == 0:
            print_success("E2E test completed successfully!")
            print_info(f"Results saved to: test_results/{test_run_id}/")
        else:
            print_error(f"E2E test failed with exit code {result.returncode}")

        return result.returncode

    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        # Clean up containers
        subprocess.run(
            ["docker", "compose", "-f", "docker-compose.local-e2e.yml", "down"], capture_output=True
        )
        return 130

    except Exception as e:
        print_error(f"Error running Docker: {e}")
        return 1


def run_without_docker(args: argparse.Namespace) -> int:
    """Run E2E test directly with Python (no Docker)."""
    print_header("Running Local E2E Test (No Docker)")

    # Set environment variables
    os.environ["FIRESTORE_EMULATOR_HOST"] = args.emulator_host
    os.environ["FIREBASE_AUTH_EMULATOR_HOST"] = args.auth_emulator_host
    os.environ["PROFILE_DATABASE_NAME"] = "(default)"
    os.environ["STORAGE_DATABASE_NAME"] = "(default)"
    os.environ["E2E_TEST_MODE"] = "true"
    os.environ["CONFIG_PATH"] = "config/config.local-e2e.yaml"

    # Generate test run ID
    test_run_id = f"e2e_local_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    output_dir = f"test_results/{test_run_id}"

    # Build command
    cmd = [
        sys.executable,
        "tests/e2e/data_collector.py",
        "--database",
        "(default)",
        "--output-dir",
        output_dir,
    ]

    if args.full:
        cmd.append("--full-mode")
    else:
        cmd.append("--fast-mode")

    if args.verbose:
        cmd.append("--verbose")

    print_info(f"Test Run ID: {test_run_id}")
    print_info(f"Emulator Host: {args.emulator_host}")
    print_info(f"Mode: {'Full' if args.full else 'Fast'}")
    print_info(f"Command: {' '.join(cmd)}")
    print()

    # Run test
    try:
        result = subprocess.run(cmd)

        if result.returncode == 0:
            print_success("E2E test completed successfully!")
            print_info(f"Results saved to: {output_dir}/")
        else:
            print_error(f"E2E test failed with exit code {result.returncode}")

        return result.returncode

    except KeyboardInterrupt:
        print_warning("\nTest interrupted by user")
        return 130

    except Exception as e:
        print_error(f"Error running test: {e}")
        return 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run local E2E tests against Firebase emulators",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fast test with Docker
  python tests/e2e/run_local_e2e.py
  
  # Full test without Docker
  python tests/e2e/run_local_e2e.py --full --no-docker
  
  # Verbose logging
  python tests/e2e/run_local_e2e.py --verbose
  
  # Custom emulator host
  python tests/e2e/run_local_e2e.py --emulator-host 192.168.1.100:8080
        """,
    )

    parser.add_argument(
        "--full",
        action="store_true",
        help="Run full E2E test (20+ jobs) instead of fast mode (4 jobs)",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "--no-docker", action="store_true", help="Run without Docker (direct Python execution)"
    )

    parser.add_argument(
        "--build", action="store_true", help="Build Docker image before running (Docker mode only)"
    )

    parser.add_argument(
        "--emulator-host",
        default="localhost:8080",
        help="Firestore emulator host:port (default: localhost:8080)",
    )

    parser.add_argument(
        "--auth-emulator-host",
        default="localhost:9099",
        help="Auth emulator host:port (default: localhost:9099)",
    )

    args = parser.parse_args()

    # Print welcome banner
    print_header("Job Finder - Local E2E Test")

    # Check prerequisites
    print_info("Checking prerequisites...")

    # Check if emulator is running
    if not check_emulator_running(args.emulator_host):
        print_error(f"Firebase emulator not running on {args.emulator_host}")
        print_info("Start emulators with: cd ~/path/to/portfolio && make firebase-emulators")
        return 1

    print_success(f"Firestore emulator is running on {args.emulator_host}")

    # Check Docker availability (if needed)
    if not args.no_docker:
        if not check_docker_available():
            print_error("Docker is not available")
            print_info("Install Docker or use --no-docker flag")
            return 1
        print_success("Docker is available")

    # Check if API keys are set
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("OPENAI_API_KEY"):
        print_warning("No AI API keys found in environment")
        print_info("Set ANTHROPIC_API_KEY or OPENAI_API_KEY for AI matching")
        print_info("⚠️  Tests will still run but AI matching will be skipped")
        print_info("⚠️  Local E2E tests use REAL AI APIs (not stubs)")
    else:
        print_success("AI API key found - tests will use REAL AI APIs")
        print_info("Note: Tests will consume API credits (~$0.01-0.05 per run)")

    print()

    # Run test
    if args.no_docker:
        return run_without_docker(args)
    else:
        return run_with_docker(args)


if __name__ == "__main__":
    sys.exit(main())
