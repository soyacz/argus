## API Design

### RESTful Principles
Use resource-based URLs with appropriate HTTP methods (GET, POST, PUT, PATCH, DELETE).

### Consistent Naming
Use lowercase, hyphenated or underscored names consistently across endpoints.

### Versioning
Implement versioning (URL path or headers) to manage breaking changes.

### Plural Nouns
Use plural nouns for resources (`/users`, `/products`).

### Limited Nesting
Keep URL nesting to 2-3 levels maximum for readability.

### Query Parameters
Use query parameters for filtering, sorting, and pagination.

### Proper Status Codes
Return appropriate HTTP status codes (200, 201, 400, 404, 500).

### Rate Limit Headers
Include rate limit information in response headers.

### Blueprint-Based Organization
Every API controller defines `bp = Blueprint(...)`, registers sub-blueprints via `bp.register_blueprint()`, and attaches `bp.register_error_handler(Exception, handle_api_exception)`.

### Status-OK Response Envelope
All endpoints return: `{"status": "ok", "response": <data>}` for success, `{"status": "error", "response": {"trace_id": ..., "exception": ..., "message": ...}}` for errors.

### Auth Decorator Pattern
API endpoints use `@api_login_required` decorator. Admin endpoints add `@check_roles(UserRoles.Admin)`. Auth decorator applied after route decorator.

### Service Layer Pattern
Business logic in service classes under `argus/backend/service/`. Each service defines a custom `<Name>Exception(Exception)`. Services instantiated per-request in controllers.
