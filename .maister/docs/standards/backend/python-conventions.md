## Python Conventions

### Python 3.12+ Target
Python code targets 3.12+ as minimum version. Configured in pyproject.toml (requires-python, ruff target-version).

### Ruff Formatter
All Python files auto-formatted with `ruff format` on commit. Enforced by pre-commit hook and CI.

### Ruff Linter Configuration
Linting with Ruff in preview mode. Selected rules: BLE (blind exceptions), F401/F821/F823/F841/F541 (pyflakes), PL/PLR (pylint), YTT, PIE, B006. Ignored: E501 (line length -- handled by formatter), PLR2004 (magic values). Note: Ruff excludes the `argus/` directory itself.

### Ruff Complexity Limits
- max-args: 12
- max-statements: 100
- max-branches: 24
- max-locals: 15

### Line Length 120
Maximum 120 characters per line. Enforced by Ruff formatter and Autopep8.

### Module-Level Logger
Every module defines: `LOGGER = logging.getLogger(__name__)` as an uppercase constant near the top.

### Absolute Imports
Use absolute imports from package root: `from argus.backend.service.testrun import TestRunService`. No relative imports.

### Type Hints (Trending)
Service methods should include type hints for parameters and return types. Currently ~54% coverage, trending toward full adoption.
