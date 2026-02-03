import logging
import os
import sys
import signal
import atexit
import cassandra.cluster
from flask import Flask, request
from prometheus_flask_exporter import NO_PREFIX
from argus.backend.error_handlers import DBErrorHandler
from argus.backend.metrics import METRICS
from argus.backend.template_filters import export_filters
from argus.backend.controller import admin, api, main
from argus.backend.cli import cli_bp
from argus.backend.util.logsetup import setup_application_logging
from argus.backend.util.encoders import ArgusJSONProvider
from argus.backend.db import ScyllaCluster
from argus.backend.controller import auth
from argus.backend.util.config import Config
from jwt import PyJWKClient

LOGGER = logging.getLogger(__name__)


# Track cleanup state to avoid double-cleanup
class _CleanupState:
    done = False
    lock = False


# Register cleanup at module level (before app initialization)
def _cleanup_on_exit():
    if _CleanupState.done or _CleanupState.lock:
        return
    _CleanupState.lock = True
    print(">>> ATEXIT: Cleaning up Scylla connections...", file=sys.stderr, flush=True)
    try:
        ScyllaCluster.shutdown()
        _CleanupState.done = True
        print(">>> ATEXIT: Scylla connections closed.", file=sys.stderr, flush=True)
    except (AttributeError, RuntimeError) as e:
        print(f">>> ATEXIT: Error during cleanup: {e}", file=sys.stderr, flush=True)
    finally:
        _CleanupState.lock = False


def _signal_handler(signum, frame):
    if _CleanupState.done or _CleanupState.lock:
        sys.exit(0)
    _CleanupState.lock = True
    print(f">>> SIGNAL {signum}: Received, cleaning up Scylla...", file=sys.stderr, flush=True)
    try:
        ScyllaCluster.shutdown()
        _CleanupState.done = True
        print(f">>> SIGNAL {signum}: Cleanup complete, exiting...", file=sys.stderr, flush=True)
    except (AttributeError, RuntimeError) as e:
        print(f">>> SIGNAL {signum}: Error during cleanup: {e}", file=sys.stderr, flush=True)
    finally:
        _CleanupState.lock = False
    sys.exit(0)


# Try to register with uwsgi.atexit if available
try:
    import uwsgi

    print(">>> Registering cleanup with uwsgi.atexit...", file=sys.stderr, flush=True)

    def _uwsgi_cleanup():
        print(">>> UWSGI.ATEXIT: Cleaning up Scylla connections...", file=sys.stderr, flush=True)
        try:
            ScyllaCluster.shutdown()
            print(">>> UWSGI.ATEXIT: Scylla connections closed.", file=sys.stderr, flush=True)
        except (AttributeError, RuntimeError) as e:
            print(f">>> UWSGI.ATEXIT: Error: {e}", file=sys.stderr, flush=True)

    uwsgi.atexit = _uwsgi_cleanup
    print(">>> uwsgi.atexit registered successfully", file=sys.stderr, flush=True)
except (ImportError, AttributeError) as e:
    print(f">>> uwsgi.atexit not available: {e}, using standard handlers", file=sys.stderr, flush=True)

atexit.register(_cleanup_on_exit)
signal.signal(signal.SIGTERM, _signal_handler)
signal.signal(signal.SIGINT, _signal_handler)
print(">>> ATEXIT handler and SIGNAL handlers registered at module level", file=sys.stderr, flush=True)


def register_metrics():
    METRICS.export_defaults(group_by="endpoint", prefix=NO_PREFIX)
    METRICS.register_default(
        METRICS.counter(
            "http_request_by_endpoint_total",
            "Total Requests made",
            labels={
                "endpoint": lambda: request.endpoint,
                "method": lambda: request.method,
                "status": lambda response: response.status,
            },
        )
    )


def start_server(config=None) -> Flask:
    app = Flask(__name__, static_url_path="/s/", static_folder="public")
    METRICS.init_app(app)
    if os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
        with app.app_context():
            METRICS.register_endpoint("/metrics")
    app.json_provider_class = ArgusJSONProvider
    app.json = ArgusJSONProvider(app)
    app.jinja_env.policies["json.dumps_kwargs"]["default"] = app.json.default
    app.config.from_mapping(Config.load_yaml_config())
    if config:
        app.config.from_mapping(config)

    if "cf" in app.config.get("LOGIN_METHODS", []):
        cf_domain = app.config.get("CLOUDFLARE_ACCESS_TEAM_DOMAIN")
        if cf_domain:
            app.config["CLOUDFLARE_ACCESS_JWK_CLIENT"] = PyJWKClient(
                f"https://{cf_domain}/cdn-cgi/access/certs",
                cache_keys=True,
                lifespan=3600,
                timeout=5,
            )
        else:
            LOGGER.warning("Cloudflare Access enabled but CLOUDFLARE_ACCESS_TEAM_DOMAIN is missing")

    setup_application_logging(log_level=app.config["APP_LOG_LEVEL"])
    app.logger.info("Starting Scylla Cluster connection...")
    app.register_error_handler(cassandra.cluster.NoHostAvailable, DBErrorHandler.handle_db_errors)
    app.register_error_handler(cassandra.cluster.NoConnectionsAvailable, DBErrorHandler.handle_db_errors)
    ScyllaCluster.get(app.config)
    ScyllaCluster.attach_to_app(app)

    app.logger.info("Loading filters...")
    for filter_func in export_filters():
        app.add_template_filter(filter_func, name=filter_func.filter_name)

    app.logger.info("Registering blueprints...")
    app.register_blueprint(auth.bp)
    app.register_blueprint(main.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(cli_bp)
    with app.app_context():
        try:
            register_metrics()
        except ValueError:
            pass

    app.logger.info("Ready.")

    return app


argus_app = start_server()
