# FreeAgent Connector — Authentication & Credentials

## Principle
Credentials are encrypted and stored in Imperal secrets storage. API tokens are never echoed in logs or error traces.

## Supported Authentication Methods
1. **OAuth 2.0 / Bearer Access Token:** Recommended for programmatic access.
2. **Environment Selection:** Support for both FreeAgent Production (`api.freeagent.com`) and Sandbox (`api.sandbox.freeagent.com`).

## Error & Security Handling
- **401 Unauthorized / 403 Forbidden:** Classify as authentication expired or insufficient scope.
- **429 Rate Limiting:** Extract `Retry-After` header and yield structured error.
- **Secret Sanitization (B8):** `_sanitize_msg` masks access tokens in error traces.
- **Multi-Tenant Scoping (B9):** Every resource call accepts `connection_id`.
