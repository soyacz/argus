# Documentation Index

**IMPORTANT**: Read this file at the beginning of any development task to understand available documentation and standards.

## Quick Reference

### Project Documentation
Project-level documentation covering architecture, technology choices, and system design for the Argus test tracking system.

### Technical Standards
Coding standards, conventions, and best practices organized by domain.

---

## Project Documentation

Located in `.maister/docs/project/`

### Tech Stack (`project/tech-stack.md`)
Technology choices and rationale for Argus: Python 3.12+ (Flask backend), TypeScript/Svelte 5 (frontend SPA), Go (CLI client), Cassandra/ScyllaDB (database). Covers frameworks, build tools (uv, Yarn, Rollup), infrastructure (Docker, nginx, uWSGI), CI/CD (GitHub Actions), monitoring (Prometheus), linting (Ruff, ESLint, Prettier), and key dependencies.

### Architecture (`project/architecture.md`)
System architecture for the Argus test tracking application: layered MVC backend with Flask blueprints (controller/service/model), component-based Svelte 5 SPA frontend with 20 Rollup entry points, Cobra-based Go CLI client, and Python client SDKs. Covers data flow (ingestion through presentation), external integrations (GitHub, Jenkins, Jira, AWS S3, Cloudflare Access), database schema (CQLEngine ORM), configuration management, and deployment architecture (Docker with nginx/uWSGI/Supervisor).

---

## Technical Standards

### Global Standards

Located in `.maister/docs/standards/global/`

#### Coding Style (`standards/global/coding-style.md`)
Naming consistency, automatic formatting, descriptive names, focused functions, uniform indentation, dead code removal, backward compatibility avoidance, and DRY principles.

#### Commenting (`standards/global/commenting.md`)
Self-documenting code practices, sparing comment usage, and avoiding change-log style comments.

#### Conventions (`standards/global/conventions.md`)
Predictable project structure, documentation upkeep, clean version control, environment variables, minimal dependencies, consistent reviews, testing standards, feature flags, changelog maintenance, conventional commits format (type/scope/subject with commitlint enforcement), no secrets in repository (detect-private-key hook, dev-db/ for local testing), pre-commit hooks enforced in CI, release via version tags (uv/PyPI/GitHub releases), consistent API envelope across stacks (`{"status","response"}`), and feature-based directory organization.

#### Error Handling (`standards/global/error-handling.md`)
Clear user messages, fail-fast validation, typed exceptions, centralized handling at boundaries, graceful degradation, retry with backoff, and resource cleanup.

#### Minimal Implementation (`standards/global/minimal-implementation.md`)
Building only what is needed, clear method purpose, removing exploration artifacts, no future stubs, no speculative abstractions, pre-commit review, and treating unused code as debt.

#### Validation (`standards/global/validation.md`)
Server-side validation, client-side feedback, early validation, specific error messages, allowlists over blocklists, type and format checks, input sanitization, business rule validation, and consistent enforcement.

### Frontend Standards

Located in `.maister/docs/standards/frontend/`

#### Accessibility (`standards/frontend/accessibility.md`)
Semantic HTML, keyboard navigation, color contrast, alt text and labels, screen reader testing, ARIA usage, heading structure, and focus management.

#### Components (`standards/frontend/components.md`)
Single responsibility, reusability, composability, clear prop interfaces, encapsulation, consistent naming, local state management, minimal props, documentation, Svelte 5 runes (`$props()`, `$state()`, `$derived()`, `run()`) over legacy reactivity, PascalCase component file naming, no direct DOM querying (use `bind:this`/actions), composition over imperative DOM updates, and function expression style (`const fn = function(...)`).

#### Code Style (`standards/frontend/code-style.md`)
Double quotes for all strings, semicolons required, 4-space indentation (ESLint/Prettier), TypeScript strict mode (`strict`, `noImplicitAny`, `forceConsistentCasingInFileNames`), and Unix (LF) line endings.

#### CSS (`standards/frontend/css.md`)
Consistent methodology (Tailwind/BEM/modules), working with frameworks, design tokens, minimizing custom CSS, and production optimization.

#### Responsive Design (`standards/frontend/responsive.md`)
Mobile-first approach, standard breakpoints, fluid layouts, relative units, cross-device testing, touch-friendly targets, mobile performance, readable typography, and content priority.

### Backend Standards

Located in `.maister/docs/standards/backend/`

#### API Design (`standards/backend/api.md`)
RESTful principles, consistent naming, versioning, plural nouns for resources, limited nesting, query parameters for filtering/sorting/pagination, proper HTTP status codes, rate limit headers. Project-specific: Blueprint-based organization, status-OK response envelope, auth decorator pattern (`@api_login_required`, `@check_roles`), and service layer pattern.

#### Python Conventions (`standards/backend/python-conventions.md`)
Python 3.12+ target, Ruff formatter (auto-format on commit), Ruff linter configuration (preview mode, selected rules), complexity limits (max-args 12, max-statements 100, max-branches 24, max-locals 15), 120-char line length, module-level LOGGER constant, absolute imports only, and type hints (trending toward full adoption).

#### Go CLI Conventions (`standards/backend/go-conventions.md`)
Go sentinel error pattern (package-level `var Err...`), internal package layout (`cli/internal/` for private packages, `cli/cmd/` for commands), and Cobra command pattern (`RunE`, `Register(parent)`).

#### Database Migrations (`standards/backend/migrations.md`)
Reversible migrations, small and focused changes, zero-downtime awareness, separating schema and data changes, careful indexing, descriptive names, and version control of migrations.

#### Models (`standards/backend/models.md`)
Clear naming conventions, timestamps for auditing, database constraints, appropriate data types, indexed foreign keys, multi-layer validation, clear relationships, and practical normalization.

#### Database Queries (`standards/backend/queries.md`)
Parameterized queries, N+1 avoidance, selecting only needed columns, strategic indexing, transactions, query timeouts, and caching expensive queries.

### Testing Standards

Located in `.maister/docs/standards/testing/`

#### Test Writing (`standards/testing/test-writing.md`)
Testing behavior over implementation, clear test names, mocking external dependencies, fast execution, risk-based testing, balanced coverage, critical path focus, appropriate depth, pytest `docker_required` marker, pytest fixtures in conftest.py (session/function scoping), Go testify assert/require usage, Go test helper pattern (`t.Helper()`), and pre-push lint/test commands.

---

## How to Use This Documentation

1. **Start Here**: Always read this INDEX.md first to understand what documentation exists
2. **Project Context**: Read relevant project documentation before starting work
3. **Standards**: Reference appropriate standards when writing code
4. **Keep Updated**: Update documentation when making significant changes
5. **Customize**: Adapt all documentation to your project's specific needs

## Updating Documentation

- Project documentation should be updated when goals, tech stack, or architecture changes
- Technical standards should be updated when team conventions evolve
- Always update INDEX.md when adding, removing, or significantly changing documentation
