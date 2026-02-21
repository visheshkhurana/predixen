# Credential Encryption - Quick Start Guide

## TL;DR

All connector credentials are now encrypted at rest. Here's what you need to do:

### For Existing Deployments

1. **Set the encryption key:**
   ```bash
   export SESSION_SECRET=$(openssl rand -hex 32)
   # OR use your existing SESSION_SECRET if already set
   ```

2. **Check encryption status:**
   ```bash
   cd /path/to/Fund-Flow
   python server/scripts/migrate_credentials.py --status
   ```

3. **Encrypt existing plaintext credentials (one-time):**
   ```bash
   # Preview what will be encrypted
   python server/scripts/migrate_credentials.py --dry-run

   # Perform encryption
   python server/scripts/migrate_credentials.py --migrate

   # Verify completion
   python server/scripts/migrate_credentials.py --verify
   ```

4. **Restart your application**

### For New Deployments

Set SESSION_SECRET, then all credentials will be encrypted automatically.

## How It Works

### Connection (Storing Credentials)

```
User provides API key → App validates → App encrypts → Database stores encrypted data
```

### Syncing (Using Credentials)

```
App retrieves encrypted data → App decrypts → Uses with API → Never stored in plaintext
```

## Security Guarantees

✓ All credentials encrypted at rest in database
✓ Only encrypted in logs (masked)
✓ Never returned in API responses
✓ Uses Fernet (AES-128 + HMAC)
✓ 100,000 iteration key derivation

## Files Overview

| Purpose | File | Action |
|---------|------|--------|
| Encryption logic | `server/core/encryption.py` | Core module (no action needed) |
| Migration tool | `server/scripts/migrate_credentials.py` | Run once to encrypt existing data |
| API integration | `server/api/connectors.py` | Automatic (no action needed) |
| Documentation | `CREDENTIAL_SECURITY.md` | Reference guide |

## Common Tasks

### Check if credentials are encrypted

```bash
python server/scripts/migrate_credentials.py --status
```

Output shows:
- Total credentials
- Encrypted count
- Plaintext count (should be 0)

### Encrypt existing plaintext credentials

```bash
# Safe preview
python server/scripts/migrate_credentials.py --dry-run

# Perform encryption
python server/scripts/migrate_credentials.py --migrate

# Verify
python server/scripts/migrate_credentials.py --verify
```

### Test encryption in Python

```python
from server.core.encryption import encrypt_credentials, decrypt_credentials

creds = {"api_key": "sk_live_test123"}
encrypted = encrypt_credentials(creds)
decrypted = decrypt_credentials(encrypted)

assert decrypted == creds  # ✓
```

### View masked credentials in logs

```python
from server.core.encryption import mask_credentials

creds = {"api_key": "sk_live_secret", "service_url": "https://api.test.com"}
masked = mask_credentials(creds)

print(f"Safe for logs: {masked}")
# Output: {'api_key': 'sk...et', 'service_url': 'https://api.test.com'}
```

## Troubleshooting

### "Failed to decrypt credentials"

Your SESSION_SECRET changed. Either:
1. Restore the original SESSION_SECRET
2. Or re-authenticate all connectors with new credentials

### Plaintext credentials still exist

Run the migration:
```bash
python server/scripts/migrate_credentials.py --migrate
```

### All credentials showing as plaintext

You might not have encrypted yet. Run:
```bash
python server/scripts/migrate_credentials.py --migrate
```

## Key Points to Remember

1. **SESSION_SECRET is critical**
   - Don't change it unless absolutely necessary
   - If changed, old credentials become unreadable
   - Store safely (env vars, secrets manager)

2. **Migration is one-time**
   - Run `--migrate` once to encrypt all existing credentials
   - After that, all new credentials are encrypted automatically

3. **Backward compatible**
   - Old plaintext credentials still work temporarily
   - Will be encrypted on next migration run

4. **No API changes**
   - All endpoints work the same
   - Encryption is transparent to users

## Next Steps

1. Read `CREDENTIAL_SECURITY.md` for full documentation
2. Run migration if you have existing credentials
3. Monitor logs for any issues
4. Keep `SESSION_SECRET` secure

## Getting Help

- **Encryption Details**: See `CREDENTIAL_SECURITY.md`
- **API Changes**: See `server/api/connectors.py`
- **Migration Issues**: See `CREDENTIAL_SECURITY.md` troubleshooting section
- **Code Questions**: See docstrings in `server/core/encryption.py`

---

**Last Updated**: February 2026
**Status**: Production Ready
