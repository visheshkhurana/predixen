# Credential Security Implementation

## Overview

This document describes the security measures implemented for storing and managing connector credentials (API keys, tokens, secrets) in FounderConsole.

## Security Architecture

### Encryption System

All sensitive connector credentials are now encrypted using **Fernet symmetric encryption** from Python's `cryptography` library.

- **Algorithm**: Fernet (AES-128 in CBC mode with HMAC)
- **Key Derivation**: PBKDF2 with SHA256 (100,000 iterations)
- **Base Key Source**: Application's `SESSION_SECRET` environment variable
- **Encryption Location**: At rest in database before storage
- **Decryption Location**: On-demand when credentials are needed for API calls

### Key Derivation

The encryption key is derived using PBKDF2:

```
Master Secret (SESSION_SECRET from env)
    ↓
PBKDF2(SHA256, iterations=100000, salt=fixed)
    ↓
32-byte encryption key
    ↓
Base64-encoded for Fernet
    ↓
Fernet cipher for encrypt/decrypt
```

**Important**: The same encryption key is derived consistently, so encrypted data can be decrypted as long as the same `SESSION_SECRET` is maintained.

## Implementation Details

### Files Modified/Created

1. **`server/core/encryption.py`** (NEW)
   - `CredentialEncryptor` class: Handles encryption/decryption
   - `get_encryptor()`: Global singleton pattern for the encryptor
   - `encrypt_credentials(dict) → str`: Encrypt credentials dict to encrypted string
   - `decrypt_credentials(str) → dict`: Decrypt encrypted string to credentials dict
   - `mask_credentials(dict) → dict`: Mask sensitive fields for logging

2. **`server/api/connectors.py`** (MODIFIED)
   - Import encryption functions
   - `connect_provider()`: Encrypt credentials before storing in database
   - `sync_provider()`: Decrypt credentials when needed for API calls
   - Never return raw credentials in API responses

3. **`server/core/credential_migration.py`** (NEW)
   - `scan_plaintext_credentials()`: Find existing plaintext credentials
   - `migrate_plaintext_credentials()`: One-time migration to encrypt existing data
   - `verify_encryption_status()`: Check encryption status across database
   - `auto_migrate_on_startup()`: Optional automatic migration on app start

4. **`server/scripts/migrate_credentials.py`** (NEW)
   - CLI tool for managing credential encryption migration
   - Commands: `--status`, `--dry-run`, `--migrate`, `--verify`

## Security Guarantees

### Data Protection

- **At Rest**: All credentials in database are encrypted
- **In Transit**: Use HTTPS/TLS (responsibility of deployment)
- **In Memory**: Credentials decrypted only when needed, promptly used
- **In Logs**: Credentials are masked using `mask_credentials()` to prevent accidental exposure

### Credential Handling

1. **On Storage** (connect_provider endpoint)
   ```python
   encrypted_creds = encrypt_credentials(credentials.credentials)
   metadata["connectors"][provider_id] = {
       "connected": True,
       "credentials": encrypted_creds,  # Stored as encrypted string
       ...
   }
   ```

2. **On Retrieval** (sync_provider endpoint)
   ```python
   if isinstance(stored_credentials, str):
       credentials_dict = decrypt_credentials(stored_credentials)
   # Use decrypted credentials for API calls
   ```

3. **In Logs**
   ```python
   masked = mask_credentials(credentials)
   logger.info(f"Credentials: {masked}")  # Safe to log
   ```

### API Response Security

- Status endpoints never include credentials in responses
- Catalog endpoints only show connection status, not credentials
- Sync endpoints don't return credentials (only sync results)
- All credential data is kept private on the server

## Migration Instructions

### For Existing Deployments

If you have existing plaintext credentials in the database:

#### Step 1: Check Status
```bash
cd /path/to/fund-flow
python server/scripts/migrate_credentials.py --status
```

This shows:
- How many companies have connectors
- How many credentials are encrypted vs plaintext
- Whether migration is needed

#### Step 2: Dry Run
```bash
python server/scripts/migrate_credentials.py --dry-run
```

This previews what will be encrypted without making changes.

#### Step 3: Perform Migration
```bash
python server/scripts/migrate_credentials.py --migrate
```

This encrypts all plaintext credentials in the database.

#### Step 4: Verify
```bash
python server/scripts/migrate_credentials.py --verify
```

This confirms all credentials are now encrypted.

### For New Deployments

No action needed. All credentials will be encrypted automatically from the first connection.

## Environment Variables

### Required

- **SESSION_SECRET**: Master secret for key derivation
  - Must be set in production
  - Used to derive the encryption key
  - If this changes, old encrypted credentials become unreadable
  - Keep this secret and secure!

### Optional

- **NODE_ENV** or **ENVIRONMENT**: Set to "production" for production deployments

## Testing the Encryption

### Manual Test

```python
from server.core.encryption import encrypt_credentials, decrypt_credentials, mask_credentials

# Original credentials
creds = {
    "api_key": "sk_live_abcd1234efgh5678",
    "client_secret": "secret_xyz789",
    "service_url": "https://api.example.com"
}

# Encrypt
encrypted = encrypt_credentials(creds)
print(f"Encrypted: {encrypted}")

# Decrypt
decrypted = decrypt_credentials(encrypted)
assert decrypted == creds

# Mask for logging
masked = mask_credentials(creds)
print(f"Masked: {masked}")
# Output: {'api_key': 'sk...78', 'client_secret': '****', 'service_url': 'https://api.example.com'}
```

### Integration Test

1. Connect a provider through the API:
   ```bash
   POST /api/connectors/companies/{company_id}/connect
   {
     "provider_id": "stripe",
     "credentials": {
       "api_key": "sk_live_..."
     }
   }
   ```

2. Check database (should be encrypted):
   ```bash
   SELECT metadata_json FROM companies WHERE id = {company_id};
   # credentials field should be an encrypted string, not plaintext
   ```

3. Trigger a sync (should work seamlessly):
   ```bash
   POST /api/connectors/companies/{company_id}/sync/stripe
   ```

## Key Security Recommendations

### Production Deployment

1. **Set Strong SESSION_SECRET**
   ```bash
   export SESSION_SECRET=$(openssl rand -hex 32)
   ```

2. **Never Commit Secrets**
   - `.env` files should be in `.gitignore`
   - Secrets should only come from environment variables or secure secret managers

3. **Key Rotation Strategy**
   - Currently: Cannot rotate keys without re-encrypting all credentials
   - Future: Implement key versioning and gradual migration
   - For now: Make SESSION_SECRET strong and protect it rigorously

4. **Database Security**
   - Use encrypted database connections (SSL/TLS)
   - Restrict database access to application server only
   - Consider full-disk encryption for database storage
   - Implement database access auditing

5. **Application Logging**
   - Never log credentials in plaintext
   - Use `mask_credentials()` when logging credential-related operations
   - Review logs for accidental credential exposure

6. **Backups**
   - Encrypted credentials remain encrypted in backups
   - Ensure backup storage is as secure as production database
   - Test backup recovery procedures

### Development/Testing

1. Use a simple test key in development
2. Generate new credentials for each test
3. Don't use production credentials in test environments
4. Clear test data after tests

## Troubleshooting

### "Failed to decrypt credentials"

**Cause**: SESSION_SECRET changed, or corrupted encrypted data

**Solution**:
1. Check if SESSION_SECRET matches what was used for encryption
2. If SESSION_SECRET is correct, the encrypted data may be corrupted
3. Re-authenticate the connector with new credentials

### Plaintext credentials still visible after migration

**Cause**: Migration not run, or migration failed partially

**Solution**:
1. Run `python server/scripts/migrate_credentials.py --status`
2. Check for any errors in the output
3. Run `--dry-run` to see what needs to be migrated
4. Run `--migrate` again if needed

### Cannot decrypt after key rotation

**Cause**: SESSION_SECRET was changed, but old encrypted data still exists

**Solution**:
1. Change SESSION_SECRET back to the original value
2. OR, re-authenticate all connectors with new credentials
3. Implement key versioning (future enhancement)

## Future Enhancements

1. **Key Versioning**
   - Store key version with encrypted data
   - Support multiple key versions simultaneously
   - Allow gradual key rotation

2. **Key Management Service**
   - Integrate with AWS KMS, Azure Key Vault, or HashiCorp Vault
   - Centralize secret management
   - Implement audit trails

3. **Credential Rotation**
   - Automatic rotation of provider credentials
   - Provider-specific rotation strategies
   - Audit trail of rotations

4. **Per-Company Encryption Keys**
   - Use separate keys for different companies
   - Enhanced isolation in multi-tenant deployments
   - Improved compliance

## Compliance & Security Standards

This implementation provides:

- ✓ Encryption at rest (AES-128)
- ✓ HMAC integrity protection
- ✓ Key derivation with PBKDF2
- ✓ Secure random generation (Fernet handles this)
- ✓ Protection against timing attacks (Fernet's HMAC)
- ✓ No plaintext in logs or responses

Suitable for compliance with:
- GDPR (data protection)
- SOC 2 Type II (encryption and access controls)
- HIPAA (if handling healthcare data)
- PCI DSS (if handling payment credentials)

## Support & Questions

For security issues or questions:
1. Review this documentation first
2. Check the encryption module docstrings
3. Run the migration script with `--status` to understand current state
4. Review application logs for encryption-related errors

---

**Last Updated**: February 2026
**Version**: 1.0
