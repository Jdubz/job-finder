#!/usr/bin/env python3
"""
Simple Flask-based job queue worker for testing.

This is a minimal version that demonstrates the Flask worker concept
without all the complex dependencies.
"""
import os
import sys
import threading
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, jsonify, request

# Global state
worker_state = {
    "running": False,
    "shutdown_requested": False,
    "items_processed_total": 0,
    "last_poll_time": None,
    "last_error": None,
    "poll_interval": 60,
    "iteration": 0,
    "start_time": None,
}

# Global worker thread reference
worker_thread: Optional[threading.Thread] = None

# Flask app
app = Flask(__name__)


def mock_worker_loop():
    """Mock worker loop that simulates job processing."""
    global worker_state  # noqa: F824

    print("🔄 Mock worker started")
    worker_state["running"] = True
    worker_state["iteration"] = 0

    while not worker_state["shutdown_requested"]:
        try:
            worker_state["iteration"] += 1
            worker_state["last_poll_time"] = time.time()

            # Simulate processing work
            print(f"📋 Mock processing iteration {worker_state['iteration']}")

            # Simulate some work
            time.sleep(2)

            # Simulate processing items
            items_this_iteration = worker_state["iteration"] % 3  # 0, 1, or 2 items
            worker_state["items_processed_total"] += items_this_iteration

            if items_this_iteration > 0:
                print(
                    f"✅ Processed {items_this_iteration} items (total: {worker_state['items_processed_total']})"
                )
            else:
                print("😴 No items to process this iteration")

            # Sleep before next poll
            time.sleep(worker_state["poll_interval"])

        except Exception as e:
            print(f"❌ Error in worker loop: {e}")
            worker_state["last_error"] = str(e)
            time.sleep(worker_state["poll_interval"])

    print("🛑 Mock worker stopped")
    worker_state["running"] = False


# Flask routes
@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify(
        {
            "status": "healthy" if worker_state["running"] else "stopped",
            "running": worker_state["running"],
            "items_processed": worker_state["items_processed_total"],
            "last_poll": worker_state["last_poll_time"],
            "iteration": worker_state["iteration"],
            "last_error": worker_state["last_error"],
        }
    )


@app.route("/status")
def status():
    """Detailed status endpoint."""
    uptime = 0
    if worker_state["start_time"]:
        uptime = time.time() - worker_state["start_time"]

    return jsonify(
        {
            "worker": worker_state,
            "uptime": uptime,
            "mock_queue": {
                "pending_items": worker_state["iteration"] % 5,
                "processed_today": worker_state["items_processed_total"],
            },
        }
    )


@app.route("/start", methods=["POST"])
def start_worker():
    """Start the worker."""
    global worker_thread

    if worker_state["running"]:
        return jsonify({"message": "Worker is already running"}), 400

    worker_state["shutdown_requested"] = False
    worker_state["start_time"] = time.time()
    worker_thread = threading.Thread(target=mock_worker_loop, daemon=True)
    worker_thread.start()

    return jsonify({"message": "Mock worker started"})


@app.route("/stop", methods=["POST"])
def stop_worker():
    """Stop the worker gracefully."""
    if not worker_state["running"]:
        return jsonify({"message": "Worker is not running"}), 400

    worker_state["shutdown_requested"] = True

    # Wait for worker to stop (with timeout)
    if worker_thread and worker_thread.is_alive():
        worker_thread.join(timeout=10)
        if worker_thread.is_alive():
            return jsonify({"message": "Worker stop requested but still running"}), 202

    return jsonify({"message": "Mock worker stopped"})


@app.route("/restart", methods=["POST"])
def restart_worker():
    """Restart the worker."""
    stop_worker()
    time.sleep(1)  # Brief pause
    return start_worker()


@app.route("/config", methods=["GET", "POST"])
def config_endpoint():
    """Get or update worker configuration."""
    if request.method == "GET":
        return jsonify(
            {
                "poll_interval": worker_state["poll_interval"],
            }
        )

    # POST - update config
    data = request.get_json() or {}
    if "poll_interval" in data:
        worker_state["poll_interval"] = max(5, int(data["poll_interval"]))  # Min 5 seconds

    return jsonify({"message": "Configuration updated"})


def main():
    """Main entry point."""
    global worker_thread

    # Start worker automatically
    worker_state["start_time"] = time.time()
    worker_thread = threading.Thread(target=mock_worker_loop, daemon=True)
    worker_thread.start()

    # Start Flask server
    port = int(os.getenv("WORKER_PORT", "5555"))
    host = os.getenv("WORKER_HOST", "0.0.0.0")

    print(f"🚀 Starting Flask worker on {host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
