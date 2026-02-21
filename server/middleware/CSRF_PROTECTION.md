# CSRF Protection Implementation

## Overview

This document describes the CSRF (Cross-Site Request Forgery) protection implemented in the FounderConsole FastAPI application using the **double-submit cookie pattern**.

## What is CSRF?

CSRF is an attack where an attacker tricks a user into making unwanted requests to a different website. For example, if a user is logged into FounderConsole and visits a malicious site, that site could craft requests to modify the user's data without the user's knowledge.

## Implementation Strategy: Double-Submit Cookie Pattern

The application uses the **double-submit cookie pattern**, which is ideal for Single Page Applications (SPAs) because:

1. **No server-side state needed** - The server doesn't need to store tokens (stateless)
2. **SPA-friendly** - JavaScript can read the token from cookies and include it in headers
3. **Simple and robust** - Relies on the browser's same-origin policy

### How It Works

1. **Token Generation**: A CSRF token (64 hex characters) is generated and stored in an HTTP cookie
2. **Client Reads Token**: The client-side application reads the token from the cookie
3. **Header Submission**: For state-changing requests (POST, PUT, PATCH, DELETE), the client includes the token in the `X-CSRF-Token` header
4. **Server Validation**: The server validates that the header token matches the cookie token
5. **Attack Prevention**: An attacker from a different origin cannot:
   - Read the token (due to same-origin policy on cookies when httpOnly=false but samesite=strict)
   - Submit a valid request (they can't read the token to include in the header)

## Implementation Details

### Server-Side Middleware

**File**: `/server/middleware/csrf_protection.py`

The `CSRFProtectionMiddleware` class provides:

- **Token Generation**: Uses `secrets.token_hex(32)` for cryptographically secure random tokens
- **Cookie Management**: Sets/refreshes tokens in cookies with appropriate security flags
- **Token Validation**: Validates token presence and format on state-changing requests
- **Path Exemptions**: Excludes certain endpoints from CSRF protection

#### Security Configuration

```python
response.set_cookie(
    key='X-CSRF-Token',
    value=new_token,
    httponly=False,          # JavaScript must be able to read it
    secure=is_secure,        # HTTPS in production, HTTP in development
    samesite='strict',       # Prevent cross-site cookie transmission
    max_age=60*60*24,        # 24-hour expiration
    path='/',
)
```

#### Exempt Endpoints

The following endpoints are exempt from CSRF protection (don't require valid tokens):

- **All GET, HEAD, OPTIONS requests** - Read-only operations, no state changes
- **Health check endpoint**: `/health` - System monitoring
- **Authentication endpoints**:
  - `/auth/register` - Uses password for security
  - `/auth/login` - Uses credentials for security
  - `/auth/admin/login` - Uses credentials for security

**Rationale**: Authentication endpoints use the credentials themselves as protection and generate tokens that can be used for subsequent requests.

#### Request Handling Flow

1. **Safe Methods (GET, HEAD, OPTIONS)**: Pass through, token is set in response for client use
2. **Exempt Paths**: Pass through without validation
3. **Unauthenticated State-Changing Requests**: Pass through (will fail at auth layer anyway)
4. **Authenticated State-Changing Requests (POST, PUT, PATCH, DELETE)**:
   - Extract token from `X-CSRF-Token` header
   - Extract token from `X-CSRF-Token` cookie
   - Validate both exist and match
   - Return 403 Forbidden if validation fails
   - Continue to handler if valid

### Client-Side Implementation

Two files have been updated to handle CSRF tokens:

#### 1. `/client/src/api/client.ts`

The main API client for making requests:

```typescript
// Get CSRF token from cookies
function getCSRFToken(): string | null {
  // Cookie parsing logic to extract X-CSRF-Token value
}

// Include CSRF token in state-changing requests
async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // ...
  const method = (options.method || 'GET').toUpperCase();
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }
  // ...
}
```

#### 2. `/client/src/lib/queryClient.ts`

Used for React Query operations:

```typescript
export async function apiRequest(method, url, data) {
  // ...
  // Include CSRF token for state-changing requests
  if (['POST', 'PUT', 'PATCH', 'DELETE'].includes(method.toUpperCase())) {
    const csrfToken = getCSRFToken();
    if (csrfToken) {
      headers['X-CSRF-Token'] = csrfToken;
    }
  }
  // ...
}
```

### CORS Configuration Update

The CORS middleware now includes `X-CSRF-Token` in allowed headers:

```python
app.add_middleware(
    CORSMiddleware,
    # ...
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
        "X-CSRF-Token"  # Added for CSRF protection
    ],
)
```

## Token Lifecycle

```
User Visits Site
    ↓
GET request to /api/companies
    ↓
Middleware generates token and sets in cookie
    ↓
Client reads token from cookie
    ↓
User submits form (POST /api/companies)
    ↓
Client includes X-CSRF-Token header with token value
    ↓
Middleware validates header token == cookie token
    ↓
If valid: Request proceeds
If invalid: 403 Forbidden response
    ↓
After successful request: New token may be generated and set
```

## Security Considerations

### Strengths

- **No server-side session state** - Scales horizontally without shared session storage
- **Resistant to common CSRF attacks** - Attacker can't read token due to same-origin policy
- **Works with SPA architecture** - Natural fit for JavaScript-based clients
- **Cryptographically secure tokens** - Uses Python's `secrets` module

### Limitations

- **Only protects authenticated requests** - Unauthenticated state-changing requests are assumed to fail at the auth layer
- **Requires secure HTTPS in production** - Tokens are not httpOnly, so HTTPS is critical
- **Depends on SameSite cookie support** - Relies on modern browser support (universal as of 2023)

### Best Practices

1. **Always use HTTPS in production** - Set `secure=true` for cookies
2. **Monitor CSRF failures** - Log and alert on high CSRF rejection rates
3. **Test token rotation** - Verify tokens are properly refreshed
4. **Validate CORS origins** - Ensure `CORS_ORIGINS` is strictly configured

## Testing CSRF Protection

### Manual Testing

1. **Test valid request**:
```bash
# First, get a token by visiting the app
# Then make a request with the token:
curl -X POST http://localhost:5000/api/companies \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: <csrf-token>" \
  -H "Cookie: X-CSRF-Token=<csrf-token>" \
  -d '{"name": "Test"}'
```

2. **Test missing CSRF token**:
```bash
curl -X POST http://localhost:5000/api/companies \
  -H "Authorization: Bearer <token>" \
  -H "Cookie: X-CSRF-Token=<csrf-token>" \
  # Note: Missing X-CSRF-Token header
  # Expected: 403 Forbidden
```

3. **Test mismatched tokens**:
```bash
curl -X POST http://localhost:5000/api/companies \
  -H "Authorization: Bearer <token>" \
  -H "X-CSRF-Token: wrong-token" \
  -H "Cookie: X-CSRF-Token=<csrf-token>" \
  # Expected: 403 Forbidden
```

### Automated Testing

The middleware includes validation of:
- Token format (64 hex characters)
- Token presence in both cookie and header
- Exact token match between cookie and header
- Proper cookie attributes (samesite=strict, secure in prod)

## Configuration

### Environment Variables

No new environment variables are required. CSRF protection uses existing settings:

- `ENVIRONMENT` - Determines if cookies should use `secure=true` (production) or `secure=false` (development)
- `CORS_ORIGINS` - Used by CORS middleware to validate cross-origin requests

### Customization

To modify CSRF protection behavior, edit `CSRFProtectionMiddleware` in `/server/middleware/csrf_protection.py`:

```python
class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, exempt_paths: list = None):
        self.exempt_paths = exempt_paths or [
            "/health",
            "/auth/register",
            "/auth/login",
            "/auth/admin/login",
        ]
```

To add exempt paths when initializing:

```python
app.add_middleware(
    CSRFProtectionMiddleware,
    exempt_paths=["/health", "/custom-webhook"]
)
```

## Middleware Order

The middleware stack is ordered correctly for security:

```python
1. CSRFProtectionMiddleware  # Validates CSRF tokens first
2. RateLimiterMiddleware      # Rate limiting to prevent abuse
3. CORSMiddleware            # Cross-origin policy
```

This order ensures:
- CSRF validation happens early (before expensive operations)
- Rate limiting protects from brute force
- CORS headers are set after all validations

## Migration Notes

### No Breaking Changes

The CSRF protection is backward compatible:

- GET/HEAD/OPTIONS requests work unchanged
- Authentication endpoints work unchanged
- Unauthenticated POST/PUT/PATCH/DELETE requests fail the same way (auth errors)
- Authenticated requests now require the CSRF token header (enforced in updated client libraries)

### Frontend Updates Required

Clients using the API must:

1. Include `X-CSRF-Token` header for state-changing requests
2. Read the token from the `X-CSRF-Token` cookie

Both `/client/src/api/client.ts` and `/client/src/lib/queryClient.ts` have been updated with this logic.

### Custom Clients

If you have custom API clients (not using the provided utilities), update them to:

```javascript
// Read CSRF token from cookie
const token = document.cookie
  .split('; ')
  .find(row => row.startsWith('X-CSRF-Token='))
  ?.split('=')[1];

// Include in state-changing requests
fetch('/api/endpoint', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': token,
    'Authorization': `Bearer ${authToken}`,
  },
  body: JSON.stringify(data),
})
```

## Debugging

### Enable Logging

CSRF validation logs are sent to the application logger. Set log level to DEBUG to see token validation details:

```python
import logging
logging.getLogger('server.middleware.csrf_protection').setLevel(logging.DEBUG)
```

### Common Issues

1. **403 Forbidden on POST requests**:
   - Ensure `X-CSRF-Token` header is included
   - Verify token value matches between cookie and header
   - Check that cookies are being sent (credentials="include" in fetch)

2. **Token not being set in cookies**:
   - First request to the API should set the token
   - Check browser's cookie storage
   - Verify SameSite and Secure flags are appropriate for your setup

3. **SameSite warnings**:
   - In development, SameSite=Strict with http:// is fine
   - In production with https://, this is the recommended setting
   - Modern browsers accept SameSite=Strict universally

## References

- [OWASP CSRF Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
- [Double Submit Cookie Pattern](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html#double-submit-cookie)
- [SameSite Cookies Explained](https://web.dev/samesite-cookies-explained/)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)
