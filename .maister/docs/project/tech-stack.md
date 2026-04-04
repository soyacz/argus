# Technology Stack

## Overview
This document describes the technology choices and rationale for Argus, a test tracking system for monitoring long-running automated test pipelines.

## Languages

### Python (3.12+)
- **Usage**: Backend API, client libraries, test infrastructure
- **Rationale**: Rich ecosystem for web services, strong database driver support, team expertise
- **Key Features Used**: Type hints (partial), dataclasses, async patterns

### TypeScript/JavaScript (ESNext)
- **Usage**: Frontend SPA, build tooling
- **Rationale**: Type safety for complex UI, Svelte ecosystem support
- **Key Features Used**: Strict mode, ES modules, type imports

### Go (1.25.4)
- **Usage**: CLI client
- **Rationale**: Cross-platform binary distribution, excellent CLI tooling ecosystem
- **Key Features Used**: Modules, goroutines, native compilation

## Frameworks

### Frontend
- **Svelte 5.37.3** — Reactive component framework with runes-based reactivity (`$props`, `$state`, `$derived`)
- **Bootstrap 5.3.7** — UI component library and responsive grid
- **Chart.js 4.5.0** — Data visualization for test results and metrics
- **FontAwesome 7.0.0** — Icon system

### Backend
- **Flask 3.0.0** — Lightweight WSGI web framework with blueprint-based routing
- **Flask-Login** — Session management and user authentication
- **Flask-WTF** — Form handling and CSRF protection
- **PyJWT (≥ 2.10.0)** — JWT-based API authentication

### CLI
- **Cobra** — CLI command framework with subcommand routing
- **Viper** — Configuration management with XDG Base Directory support

### Testing
- **pytest 8.3.5** — Python test framework with parallel execution (xdist), coverage (pytest-cov), and custom reporter (pytest-argus-reporter)

## Database

### Cassandra / ScyllaDB
- **Type**: NoSQL (wide-column store)
- **Driver**: scylla-driver ≥ 3.29.4
- **Rationale**: High-throughput write performance for test result ingestion, horizontal scalability
- **Schema Management**: CQLEngine ORM with managed schema creation

## Build Tools & Package Management

| Tool | Purpose | Version |
|------|---------|---------|
| **uv** (astral) | Python package management | Latest |
| **Yarn** | Node.js package management | 1.22.22 |
| **Rollup** | Frontend bundling (20 entry points) | 4.46.2 |
| **pre-commit** | Git hook management | Configured |

## Infrastructure

### Containerization
- **Docker** — Production container with multi-stage build
- **docker-compose** — Development database setup (dev-db/)

### CI/CD
- **GitHub Actions** — Automated testing and CI workflows (.github/workflows/)

### Deployment
- **nginx** — Reverse proxy
- **uWSGI 2.0.20** — WSGI application server
- **Supervisor 4.2.4** — Process management within Docker containers

### Monitoring
- **Prometheus** — Metrics via prometheus-flask-exporter (≥ 0.23.2)

## Development Tools

### Linting & Formatting
- **Ruff** — Python linter (preview mode, line-length 120)
- **Autopep8** — Python formatting
- **ESLint 9.32.0** — TypeScript/JavaScript linting with TypeScript plugin
- **Prettier 3.6.2** — Code formatting (frontend)

### Type Checking
- **TypeScript** — Strict mode enabled (tsconfig.json)
- **Python type hints** — Partial coverage (modern modules typed, legacy modules untyped)

### Commit Standards
- **Conventional Commits** — Enforced via commitlint.config.js
- **Format**: `type(scope): message` (e.g., `feature(cli):`, `fix(frontend):`)

## Key Dependencies

### Backend
- PyGithub (≥ 2.6.1) — GitHub API integration
- python-jenkins (≥ 1.7.0) — Jenkins CI integration
- jira (≥ 3.10.5) — Jira issue tracker integration
- boto3 (~= 1.38.9) — AWS S3 storage
- Click (8.1.3+) — Python CLI utilities

### Frontend
- marked (16.1.2) + highlight.js (11.5.0) — Markdown rendering with syntax highlighting
- DOMPurify (3.2.6) — XSS sanitization
- date-fns (4.1.0) — Date manipulation
- lz-string (1.4.4) — Data compression
- yaml (2.8.2) — YAML parsing

### CLI
- tablewriter (olekukonko) — Formatted table output
- testify (stretchr) — Test assertions
- xdg (adrg) — Cross-platform config directories
- keychain — Native OS credential storage

## Version Management
- Python: Pinned in pyproject.toml with minimum version constraints
- Node.js: Pinned in package.json with Yarn lockfile
- Go: Go modules (go.mod/go.sum)
- Infrastructure: Docker image versions in Dockerfile

---
*Last Updated*: 2026-04-04
*Auto-detected*: Languages, frameworks, versions, dependencies, build tools, infrastructure, linting, testing frameworks
