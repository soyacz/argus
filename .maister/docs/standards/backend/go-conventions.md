## Go CLI Conventions

### Go Sentinel Error Pattern
Define sentinel errors as package-level variables: `var ErrInvalidBaseURL = errors.New("api: invalid base URL")`. Wrap errors with `fmt.Errorf("context: %w", err)`.

### Internal Package Layout
Use `cli/internal/` for private packages (api, auth, cache, config, jwt, keychain, logging, models, output, services). Commands in `cli/cmd/`. No `pkg/` directory.

### Cobra Command Pattern
Commands defined as `var cmd = &cobra.Command{...}` with `RunE` for error-returning handlers. Register in `init()`. Sub-command packages use `Register(parent)` pattern.
