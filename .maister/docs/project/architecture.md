# System Architecture

## Overview
Argus is a mixed-stack test tracking application with three main components: a Python/Flask REST API backend, a Svelte 5 SPA frontend, and a Go CLI client. The system ingests test results from automated pipelines, stores them in Cassandra/ScyllaDB, and provides dashboards for monitoring, release planning, and team coordination.

## Architecture Pattern
**Pattern**: Layered MVC (Backend) + Component-Based SPA (Frontend) + Cobra CLI

The backend follows a controller → service → model layering with Flask blueprints for route organization. The frontend is a multi-entry Svelte SPA with feature-based module organization. The CLI provides direct API access for automation and developer workflows.

## System Structure

### Backend API (`argus/backend/`)
- **Controller Layer** (`controller/`): Flask blueprints — `api.py`, `admin.py`, `main.py`, `auth.py`, plus feature-specific blueprints (`testrun_api`, `team`, `planner_api`, `view_api`, `notifications`, `client_api`)
- **Service Layer** (`service/`): Business logic — `argus_service.py`, `results_service.py`, `testrun.py`, `user.py`
- **Model Layer** (`models/`): Cassandra ORM table definitions (`web.py`)
- **Plugin System** (`plugins/`): Extensible test framework integrations — `core.py` (base), plus `jira`, `jenkins`, and framework-specific plugins
- **Events** (`events/`): Event publishing and handling
- **Entry Point**: `argus_backend.py::start_server()`

### Client Libraries (`argus/client/`)
- **Purpose**: Python client SDKs for submitting test results to the API
- **Variants**: `generic/` (generic tests), `sct/` (SCT-specific), `driver_matrix_tests/` (ScyllaDB driver tests), `sirenada/`
- **Key Files**: Each variant has its own client module and test suite

### Frontend SPA (`frontend/`)
- **Feature Modules** (18+): `TestRun/`, `ReleasePlanner/`, `AdminPanel/`, `Discussion/`, `Schedule/`, `Profile/`, etc.
- **Shared Utilities** (`Common/`): `DateUtils.ts`, `TextUtils.ts`, `UserUtils.ts`
- **State Management** (`Stores/`): Svelte stores for global application state
- **Entry Points**: 20 Rollup bundles (`main`, `workArea`, `adminPanel`, `login`, etc.)
- **Build**: Rollup 4.46.2 with multiple plugins (`rollup.config.js`)

### CLI Client (`cli/`)
- **Commands** (`cmd/`): Cobra-based verb subcommands — `root.go` + feature commands (discussions, comments, test runs)
- **Internal Packages** (`internal/`): `api/` (REST client), `auth/` (JWT), `cache/` (file-based TTL cache), `config/` (Viper), `keychain/` (OS credentials), `output/` (table/JSON formatting), `services/` (high-level operations), `models/` (data types)

### Custom pytest Plugin (`pytest-argus-reporter/`)
- **Purpose**: pytest plugin for automatically reporting test results to the Argus API
- **Distribution**: Standalone package with its own setup

## Data Flow

```
Test Pipeline → Client SDK/CLI → REST API → Service Layer → Cassandra/ScyllaDB
                                                                    ↓
                  Frontend SPA ← REST API ← Service Layer ← Query/Aggregate
```

1. **Ingestion**: Test pipelines use Python client SDKs or the Go CLI to submit results via the REST API
2. **Processing**: The service layer validates, transforms, and stores results in Cassandra
3. **Querying**: The frontend SPA fetches aggregated results via REST endpoints
4. **Presentation**: Dashboards display test runs, release status, and team metrics

## External Integrations

| Integration | Library | Purpose |
|-------------|---------|---------|
| **GitHub** | PyGithub | Repository and PR status tracking |
| **Jenkins** | python-jenkins | CI job monitoring and result correlation |
| **Jira** | jira | Issue linking and bug tracking |
| **AWS S3** | boto3 | Artifact and log storage |
| **Cloudflare Access** | Custom middleware | SSO authentication |
| **Prometheus** | prometheus-flask-exporter | Application metrics export |

## Database Schema
- **Engine**: CQLEngine ORM with managed schema
- **Models**: Defined in `argus/backend/models/web.py`
- **Migrations**: Python scripts in `scripts/migration/`
- **Development DB**: docker-compose setup in `dev-db/`

## Configuration
- **Application Config**: YAML files (`argus.yaml`, `argus_web.yaml`) with environment variable overrides
- **Example Configs**: `argus_web.example.yaml` provided for reference
- **CLI Config**: Viper-based with XDG Base Directory support
- **Environment Variables**: `.env` files for sensitive values (not committed)

## Deployment Architecture

```
┌─────────────────────────────────────────┐
│              Docker Container           │
│  ┌───────────┐  ┌────────────────────┐  │
│  │   nginx   │→ │  uWSGI + Flask     │  │
│  │  (proxy)  │  │  (app server)      │  │
│  └───────────┘  └────────────────────┘  │
│       ↑              ↑                  │
│  Static assets   Supervisor             │
│  (compiled JS)   (process mgmt)         │
└─────────────────────────────────────────┘
              ↓
     ┌──────────────┐
     │  Cassandra /  │
     │  ScyllaDB     │
     └──────────────┘
```

- **Reverse Proxy**: nginx serves static assets and proxies API requests to uWSGI
- **App Server**: uWSGI runs the Flask application
- **Process Manager**: Supervisor manages nginx and uWSGI within the container
- **Database**: Cassandra/ScyllaDB runs separately (external or docker-compose for dev)

---
*Based on codebase analysis performed 2026-04-04*
