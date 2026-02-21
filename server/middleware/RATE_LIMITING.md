# Rate Limiting Middleware

## Overview

The FounderConsole API includes a robust rate limiting middleware to protect against brute force attacks and DDoS (Distributed Denial of Service) attacks. The implementation uses an **in-memory token bucket algorithm** that requires no external dependencies beyond FastAPI/Starlette.

## Problem Solved

**Without rate limiting, the API is vulnerable to:**
- Brute force attacks on authentication endpoints (login, register)
- DDoS attacks from a single IP or botnet
- Resource exhaustion from abusive clients
- Credential stuffing and account takeover attempts

## Implementation Details

### Token Bucket Algorithm

The rate limiter uses a classic token bucket algorithm:

1. Each IP address (or user) has a "bucket" that starts full with tokens
2. Each request consumes 1 token
3. Tokens are automatically refilled at a configured rate (e.g., 5 tokens/minute)
4. When the bucket is empty, requests are rejected with a 429 Too Many Requests response
5. The `Retry-After` header tells clients when they can try again

### Benefits

- **Efficient**: O(1) memory per client with automatic cleanup of idle clients
- **Fair**: Each client gets their own allocation
- **Transparent**: Built on HTTP standards (429 status code, Retry-After header)
- **No Dependencies**: Uses Python standard library only
- **Configurable**: Easy to adjust per endpoint category

## Configuration

Rate limits are applied per endpoint category and can be configured via:

1. **Environment Variables** (recommended for production)
2. **Constructor Parameters** (for testing or programmatic control)

### Environment Variables

```bash
# Auth endpoints (login, register, admin/login)
RATE_LIMIT_AUTH=5          # 5 requests/minute per IP

# General API endpoints
RATE_LIMIT_API=60          # 60 requests/minute per IP

# Upload endpoints
RATE_LIMIT_UPLOAD=10       # 10 requests/minute per IP
```

### Example .env Configuration

```env
# Production rate limiting (stricter)
RATE_LIMIT_AUTH=3          # 3 login attempts per minute per IP
RATE_LIMIT_API=30          # 30 API calls per minute per IP
RATE_LIMIT_UPLOAD=5        # 5 uploads per minute per IP

# Development (more relaxed for testing)
RATE_LIMIT_AUTH=60
RATE_LIMIT_API=600
RATE_LIMIT_UPLOAD=100
```

## Endpoint Categories

### Auth Endpoints (5 req/min default)
```
POST /auth/login
POST /auth/register
POST /auth/admin/login
```

**Use case**: Protect against brute force credential attacks
**Typical value**: 3-5 requests/minute (one login attempt every 12-20 seconds)

### Upload Endpoints (10 req/min default)
```
POST /csv-import
POST /api/upload
```

**Use case**: Prevent resource exhaustion from large file uploads
**Typical value**: 5-10 uploads/minute

### API Endpoints (60 req/min default)
```
GET /companies
POST /simulations
PUT /decisions/:id
DELETE /scenarios/:id
(all other endpoints)
```

**Use case**: Reasonable rate limit for normal API usage
**Typical value**: 60-120 requests/minute

### Health Endpoints (No Limit)
```
GET /health
GET /
```

**Use case**: Allow monitoring systems to check health without rate limiting

## Usage Examples

### User Perspective: Handling Rate Limits

When a client exceeds the rate limit, they receive:

```json
HTTP/1.1 429 Too Many Requests
Retry-After: 45
Content-Type: application/json

{
  "detail": "Rate limit exceeded. Maximum 5 requests per minute.",
  "retry_after": 45
}
```

**Client should:**
1. Stop sending requests to that endpoint
2. Wait at least `Retry-After` seconds before retrying
3. Consider implementing exponential backoff

### JavaScript/Fetch Example

```javascript
async function makeRequest(url) {
  let retries = 0;
  const maxRetries = 3;

  while (retries < maxRetries) {
    const response = await fetch(url);

    if (response.status === 429) {
      const retryAfter = parseInt(response.headers.get('Retry-After'));
      console.log(`Rate limited. Waiting ${retryAfter} seconds...`);
      await new Promise(resolve => setTimeout(resolve, retryAfter * 1000));
      retries++;
      continue;
    }

    return response;
  }

  throw new Error('Max retries exceeded');
}
```

### Python/Requests Example

```python
import requests
import time

def make_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

## Monitoring

### Response Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 60
X-RateLimit-Category: api
```

**Fields:**
- `X-RateLimit-Limit`: Maximum requests per minute for this category
- `X-RateLimit-Category`: The category the endpoint belongs to (auth, api, upload, health)

### Logging

Rate limit violations are logged with details:

```python
logger.warning(
    f"Rate limit exceeded: 192.168.1.42 (auth), "
    f"retry_after=45s, limit=5/min"
)
```

### Metrics You Can Track

- Count of 429 responses by endpoint category
- Count of 429 responses by client IP
- Distribution of retry_after values
- Which endpoints are most frequently rate limited

## Security Considerations

### Protected Scenarios

✅ **Brute Force Attacks**: Limited to 5 login attempts/minute per IP
```
Attacker tries: 100 passwords in 1 minute
Server allows: 5 attempts, rejects rest
Result: Attacker needs ~20 minutes for 100 attempts
```

✅ **DDoS from Single IP**: Requests exceed 60/minute
```
Rate limit enforces: 1 request per second maximum
Large files: Limited to 10 uploads/minute = more fair resource usage
```

✅ **Credential Stuffing**: Can't spray credentials across accounts quickly
```
With limit: Must wait 12 seconds between attempts
Botnet bypass: Requires distributing across many IPs
```

### Limitations

❌ **Distributed DDoS**: Attackers using many IPs can still overwhelm
- **Mitigation**: Use a reverse proxy (nginx) or WAF with global rate limiting

❌ **Authenticated Users**: All users share the same per-IP limit
- **Future Enhancement**: Could track per-user_id instead of IP

❌ **Spoofed X-Forwarded-For**: Attacker behind proxy can fake their IP
- **Mitigation**: Only trust X-Forwarded-For from known proxies

## Performance Impact

### Memory Usage

- ~100 bytes per active IP address (token bucket + metadata)
- Automatic cleanup removes idle clients after 1 hour
- 1000 concurrent users = ~100 KB memory overhead

### CPU Impact

- **Per request**: O(1) time complexity for rate limit check
- **Cleanup**: Runs every 1000 requests, removes stale entries
- **Negligible**: < 1ms overhead per request

### Scalability

For **horizontal scaling** (multiple servers):

**Current Implementation**:
- ✅ Works great for single server or load balanced with sticky sessions
- ❌ Each server has independent rate limit buckets
- ❌ Attackers can distribute requests across servers to bypass limits

**For Production (Multiple Servers)**:

Option 1: Use sticky sessions (load balancer sends same IP to same server)
```nginx
# nginx example
upstream backend {
    server server1:8000;
    server server2:8000;
    hash $remote_addr;  # Hash-based load balancing
}
```

Option 2: Upgrade to Redis-based rate limiter (future enhancement)
```python
# Pseudo-code for future implementation
from redis import Redis
redis_client = Redis()
# Share rate limit buckets across all servers
```

Option 3: WAF/Reverse Proxy Rate Limiting
```nginx
# nginx rate limiting (server-side, shared across all backends)
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;
limit_req zone=auth_limit burst=10 nodelay;
```

## Testing

### Unit Tests

```bash
pytest server/middleware/test_rate_limiter.py -v
```

Tests cover:
- Token bucket algorithm (refill, capacity limits)
- Endpoint category detection
- Rate limit enforcement
- Response format (429 status, Retry-After header)
- Multiple IPs with separate limits
- Environment variable configuration

### Manual Testing

```bash
# Test auth endpoint rate limiting
for i in {1..10}; do
  curl -X POST http://localhost:8000/auth/login \
    -H "Content-Type: application/json" \
    -d '{"email":"test@example.com","password":"test"}' \
    -w "Status: %{http_code}\n"
  sleep 0.1
done

# Check rate limit headers
curl -i http://localhost:8000/api/companies | grep X-RateLimit

# Check response after rate limit exceeded
curl -i http://localhost:8000/api/companies | grep Retry-After
```

### Load Testing

```bash
# Using Apache Bench
ab -n 100 -c 10 http://localhost:8000/api/companies

# Using wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/companies
```

## Troubleshooting

### "Rate limited but haven't sent that many requests"

**Possible causes:**
1. Other clients behind same IP (shared ISP, corporate network)
2. Browser making multiple requests (favicon, CSS, JS)
3. Monitoring/health check requests consuming limit

**Solution:**
- Use authentication (track per user_id instead of IP)
- Exclude static assets from rate limiting
- Whitelist trusted monitoring IPs

### Rate limits too strict for legitimate usage

**Solution:**
Increase limits via environment variables:
```bash
RATE_LIMIT_API=300  # 5 req/sec instead of 1 req/sec
```

### Rate limits not enforcing

**Check:**
1. Is middleware added to the app? → Check main.py
2. Are environment variables set correctly? → Check logs on startup
3. Is X-Forwarded-For being trusted incorrectly? → Only trust from your proxy

## Future Enhancements

1. **Per-User Rate Limiting**: Track by `user_id` from JWT token instead of IP
2. **Redis Backend**: Share rate limits across multiple servers
3. **Tiered Rate Limits**: Different limits for free vs premium users
4. **Time-Based Limits**: Stricter limits during off-hours
5. **Circuit Breaker**: Temporarily block IPs with repeated rate violations
6. **Analytics**: Dashboard showing rate limit violations and patterns

## References

- [RFC 6585 - HTTP 429 Too Many Requests](https://tools.ietf.org/html/rfc6585)
- [Token Bucket Algorithm](https://en.wikipedia.org/wiki/Token_bucket)
- [OWASP Rate Limiting](https://owasp.org/www-community/attacks/Brute_force_attack)
- [FastAPI Middleware Documentation](https://fastapi.tiangolo.com/tutorial/middleware/)
