## Development Conventions

### Predictable Structure
Organize files and directories in a logical, navigable layout.

### Up-to-Date Documentation
Keep README files current with setup steps, architecture overview, and contribution guidelines.

### Clean Version Control
Write clear commit messages, use feature branches, and add meaningful descriptions to pull requests.

### Environment Variables
Store configuration in environment variables; never commit secrets or API keys.

### Minimal Dependencies
Keep dependencies lean and up-to-date; document why major ones are included.

### Consistent Reviews
Follow a defined code review process with clear expectations for reviewers and authors.

### Testing Standards
Define required test coverage (unit, integration, etc.) before merging.

### Feature Flags
Use flags for incomplete features instead of long-lived branches.

### Changelog Updates
Maintain a changelog or release notes for significant changes.

### Build What's Needed
Avoid speculative code and "just in case" additions (see minimal-implementation.md).

### Conventional Commits
Commit messages must follow format: `type(scope): subject`. Types restricted to: ci, docs, feature, fix, improvement, perf, refactor, revert, style, test, unit-test. Scope is required (min 5 chars). Subject: 10-85 chars. Header max 72 chars. Body required (min 30 chars, max 100 chars/line, leading blank line). Enforced by commitlint pre-commit hook.

```
feature(backend): add user authentication endpoint
fix(frontend): resolve null pointer in test run details
refactor(cli): extract shared utility functions
```

### No Secrets in Repository
Never commit secrets, private keys, or credentials. Enforced by detect-private-key pre-commit hook. Use Docker compose setup in `dev-db/` for testing against Cassandra.

### Pre-commit Hooks Enforced in CI
All pre-commit hooks run in CI on every push/PR to master via `pre-commit run --all-files`, catching any local bypasses.

### Release via Version Tags
Releases triggered by pushing `v*` tags. Packages built with uv and published to PyPI using trusted publishing. GitHub releases created automatically.

### Consistent API Envelope Across Stacks
All three stacks (Python backend, Go CLI, JS frontend) share a common API envelope: `{"status": "ok"|"error", "response": <payload>}`. Go CLI uses typed generics `APIResponse[T]`, frontend checks `res.status === 'ok'`.

### Feature-Based Directory Organization
Organize files by feature/domain rather than technical layer. Backend: `controller/`, `service/`, `models/`. Frontend: `AdminPanel/`, `ReleaseDashboard/`, `TestRun/`. CLI: `internal/{api,auth,cache,...}`.
