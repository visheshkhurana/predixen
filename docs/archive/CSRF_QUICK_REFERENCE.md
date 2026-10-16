# CSRF Protection Quick Reference

## What Changed?

CSRF protection has been added to all POST, PUT, PATCH, and DELETE endpoints. The frontend automatically handles it, but here's what you need to know.

## For Frontend Developers

### Automatic Handling

Both main API client files automatically include CSRF tokens:
- `/client/src/api/client.ts` - Main API client
- `/client/src/lib/queryClient.ts` - React Query client

**No changes needed to existing code** - CSRF tokens are handled transparently.

### How It Works

1. Browser reads `X-CSRF-Token` from cookies automatically
2. Client includes it in `X-CSRF-Token` header for state-changing requests
3. Server validates the token matches

### Testing the Client

```bash
# After login, these should all work:
POST /api/companies          # ✅ CSRF token automatically included
PUT /api/companies/1         # ✅ CSRF token automatically included
PATCH /api/companies/1       # ✅ CSRF token automatically included
DELETE /api/companies/1      # ✅ CSRF token automatically included

# Read operations don't need CSRF token:
GET /api/companies           # ✅ Works without token
```

### Custom API Calls

If you make direct fetch calls (not using the provided clients):

```javascript
// Read the CSRF token
const token = document.cookie
  .split('; ')
  .find(row => row.startsWith('X-CSRF-Token='))
  ?.split('=')[1];

// Include it in state-changing requests
fetch('/api/companies', {
  method: 'POST',
  headers: {
    'X-CSRF-Token': token,  // Add this for POST/PUT/PATCH/DELETE
    'Authorization': `Bearer ${authToken}`,
  },
  body: JSON.stringify(data),
})
```

## For Backend Developers

### What's Protected

All routes automatically get CSRF protection:
- POST requests (create operations)
- PUT requests (full updates)
- PATCH requests (partial updates)
- DELETE requests (deletions)

### What's Exempt

- GET/HEAD/OPTIONS requests (read-only)
- `/health` endpoint
- `/auth/register`, `/auth/login`, `/auth/admin/login` (use credentials)
- Unauthenticated requests (fail auth anyway)

### Adding New Routes

CSRF protection is automatic for new state-changing routes:

```python
@router.post("/new-endpoint")
async def new_endpoint(current_user = Depends(get_current_user)):
    # Automatically protected by CSRF middleware
    # Client must include X-CSRF-Token header
    return {"status": "success"}
```

### Customizing Exempt Paths

To add exempt paths, modify `/server/main.py`:

```python
app.add_middleware(
    CSRFProtectionMiddleware,
    exempt_paths=["/health", "/auth/login", "/webhooks/stripe"]
)
```

## Files Modified

| File | Changes | Impact |
|------|---------|--------|
| `/server/main.py` | Added CSRF middleware, updated CORS headers | All state-changing requests now require CSRF token |
| `/server/middleware/csrf_protection.py` | **NEW** - Middleware implementation | Validates CSRF tokens on protected endpoints |
| `/client/src/api/client.ts` | Added CSRF token reading and header inclusion | Automatically includes token in state-changing requests |
| `/client/src/lib/queryClient.ts` | Added CSRF token reading and header inclusion | React Query mutations automatically include token |

## Documentation

- **Full Details**: `/server/middleware/CSRF_PROTECTION.md`
- **Implementation Summary**: `/CSRF_IMPLEMENTATION_SUMMARY.md`
- **This File**: `/CSRF_QUICK_REFERENCE.md`

## Common Questions

### Q: Do I need to update my API calls?

**A**: No, the provided API clients handle CSRF automatically. If you use custom code, add the `X-CSRF-Token` header for state-changing requests.

### Q: What if CSRF validation fails?

**A**: You'll get a 403 Forbidden response. This means:
1. CSRF token wasn't included in the request header
2. Token doesn't match between cookie and header
3. Token has invalid format

Check:
- Browser has cookies enabled
- Client is including `X-CSRF-Token` header
- Token value in cookie matches header value

### Q: Does this affect read operations (GET)?

**A**: No, GET requests don't require CSRF tokens. Only POST, PUT, PATCH, DELETE.

### Q: How is the token generated?

**A**: Using Python's `secrets.token_hex(32)` for 64 character cryptographically secure tokens.

### Q: Is this required in production?

**A**: Yes, CSRF protection is essential for production. It prevents attackers from tricking users into modifying their data.

### Q: What about API rate limiting?

**A**: CSRF and rate limiting are separate. Rate limiting still applies as before.

### Q: Do I need to do anything for HTTPS in production?

**A**: The middleware automatically sets `secure=true` for cookies when using HTTPS, which is correct for production.

## Security Checklist

Before deploying:

- [x] Frontend clients updated with CSRF handling
- [x] Middleware added to server
- [x] CORS headers include X-CSRF-Token
- [x] HTTPS enabled in production
- [ ] Tested POST/PUT/PATCH/DELETE requests work
- [ ] Tested CSRF rejection when token is missing
- [ ] Monitored logs for CSRF failures

## Troubleshooting

### 403 Forbidden on POST requests

**Checklist**:
1. Are cookies enabled in browser?
2. Do you see `X-CSRF-Token` in browser cookies?
3. Does the value match between cookie and `X-CSRF-Token` header?
4. Is the request authenticated (has Authorization header)?

### Token not in cookies

**Solution**: Make an initial GET request first to set the token.

### CORS errors

**Check**: Is `X-CSRF-Token` in CORS allow_headers in `main.py`? (It is)

## Quick Implementation Checklist

- [x] Middleware created (`/server/middleware/csrf_protection.py`)
- [x] Server integrated (`/server/main.py` updated)
- [x] Frontend API client updated (`/client/src/api/client.ts`)
- [x] React Query client updated (`/client/src/lib/queryClient.ts`)
- [x] CORS headers updated to allow X-CSRF-Token
- [x] Documentation created
- [x] No new dependencies needed
- [x] Backward compatible with existing code

## Support

For detailed technical documentation, see `/server/middleware/CSRF_PROTECTION.md`.

For implementation overview, see `/CSRF_IMPLEMENTATION_SUMMARY.md`.
