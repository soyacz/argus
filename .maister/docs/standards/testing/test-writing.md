## Test Writing

### Test Behavior
Focus on what code does, not how it does it, to allow safe refactoring.

### Clear Names
Use descriptive names explaining what's tested and expected (`shouldReturnErrorWhenUserNotFound`).

### Mock External Dependencies
Isolate tests by mocking databases, APIs, and external services.

### Fast Execution
Keep unit tests fast (milliseconds) so developers run them frequently.

### Risk-Based Testing
Prioritize testing based on business criticality and likelihood of bugs.

### Balance Coverage and Velocity
Adjust test coverage based on project needs and team workflow.

### Critical Path Focus
Ensure core user workflows and critical business logic are well-tested.

### Appropriate Depth
Match edge case testing to the risk profile of the code.

### Pytest Docker Required Marker
Tests requiring Docker must be marked with `@pytest.mark.docker_required`. Defined in pyproject.toml.

### Pytest Fixtures in conftest.py
Share test fixtures via `conftest.py`. Use session-scoped fixtures for database setup (`argus_db`), function-scoped for services and test data. Use dependency injection.

### Go testify assert/require
Go tests use testify library exclusively:
- `assert.*` for non-fatal checks
- `require.*` for fatal preconditions (stops test on failure)
- Test naming: `TestFunctionName_Scenario` (e.g., `TestNew_ValidURL`)

### Go Test Helper Pattern
Define helper functions that call `t.Helper()` as first statement. Use `t.TempDir()` for temporary files. Keep helpers unexported at top of test files.

```go
func okEnvelope(t *testing.T, payload any) []byte {
    t.Helper()
    // ...
}
```

### Run Lint and Tests Before Pushing
Always run `uv run ruff check` and `uv run pytest argus/backend/tests` before pushing. Pre-commit hooks also enforce this.
