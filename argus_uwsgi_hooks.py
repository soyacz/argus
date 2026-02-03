"""
uWSGI hooks for graceful shutdown.
"""

import sys
import logging

LOGGER = logging.getLogger(__name__)

# Print on module load to confirm it's being imported
print(">>> UWSGI HOOKS MODULE LOADED <<<", file=sys.stderr, flush=True)


def cleanup_scylla_connections():
    """Clean up Scylla connections on worker shutdown."""
    # Use print to stderr since logging might not be configured
    print(">>> UWSGI HOOK: cleanup_scylla_connections() called", file=sys.stderr, flush=True)
    try:
        from argus.backend.db import ScyllaCluster

        print(">>> UWSGI HOOK: Calling ScyllaCluster.shutdown()...", file=sys.stderr, flush=True)
        ScyllaCluster.shutdown()
        print(">>> UWSGI HOOK: ScyllaCluster.shutdown() completed", file=sys.stderr, flush=True)
        LOGGER.info("Scylla connections closed.")
    except Exception as e:  # noqa: BLE001
        print(f">>> UWSGI HOOK: Error during shutdown: {e}", file=sys.stderr, flush=True)
        LOGGER.error("Error during Scylla shutdown: %s", e)
