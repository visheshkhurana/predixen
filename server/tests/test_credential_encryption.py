"""
Tests for credential encryption and decryption functionality.

Tests encryption module integration with the connector API endpoints.
"""

import pytest
import json
from typing import Dict, Any

from server.core.encryption import (
    CredentialEncryptor,
    encrypt_credentials,
    decrypt_credentials,
    mask_credentials,
    get_encryptor,
)


class TestCredentialEncryptor:
    """Tests for the CredentialEncryptor class."""

    def test_encrypt_decrypt_roundtrip(self):
        """Test that encrypted data can be decrypted back to original."""
        encryptor = CredentialEncryptor("test-secret-key-123")

        original = {
            "api_key": "sk_live_abc123def456",
            "client_secret": "secret_xyz789",
            "service_url": "https://api.example.com",
            "other_field": "value"
        }

        encrypted = encryptor.encrypt_credentials(original)
        decrypted = encryptor.decrypt_credentials(encrypted)

        assert decrypted == original

    def test_encrypt_returns_string(self):
        """Test that encrypt_credentials returns a string."""
        encryptor = CredentialEncryptor("test-secret")
        result = encryptor.encrypt_credentials({"key": "value"})
        assert isinstance(result, str)

    def test_different_keys_produce_different_encrypted_data(self):
        """Test that same data encrypted with different keys produces different results."""
        data = {"api_key": "test123"}

        encrypted1 = CredentialEncryptor("key1").encrypt_credentials(data)
        encrypted2 = CredentialEncryptor("key2").encrypt_credentials(data)

        # Even though we're encrypting the same data, different keys should produce different outputs
        assert encrypted1 != encrypted2

    def test_decrypt_with_wrong_key_fails(self):
        """Test that decryption with wrong key raises ValueError."""
        encryptor = CredentialEncryptor("correct-key")
        data = {"secret": "value"}

        encrypted = encryptor.encrypt_credentials(data)

        wrong_encryptor = CredentialEncryptor("wrong-key")
        with pytest.raises(ValueError):
            wrong_encryptor.decrypt_credentials(encrypted)

    def test_empty_credentials_dict(self):
        """Test handling of empty credentials dictionary."""
        encryptor = CredentialEncryptor("test-key")
        empty = {}

        encrypted = encryptor.encrypt_credentials(empty)
        decrypted = encryptor.decrypt_credentials(encrypted)

        assert decrypted == empty

    def test_credentials_with_special_characters(self):
        """Test encryption of credentials with special characters."""
        encryptor = CredentialEncryptor("test-key")

        credentials = {
            "api_key": "sk_live_@#$%^&*()",
            "secret": "pass=word;with&special|chars",
            "unicode": "こんにちは",
            "nested": {"key": "value"}
        }

        encrypted = encryptor.encrypt_credentials(credentials)
        decrypted = encryptor.decrypt_credentials(encrypted)

        assert decrypted == credentials

    def test_encrypt_rejects_non_dict(self):
        """Test that encrypt_credentials rejects non-dict inputs."""
        encryptor = CredentialEncryptor("test-key")

        with pytest.raises(TypeError):
            encryptor.encrypt_credentials("not a dict")

        with pytest.raises(TypeError):
            encryptor.encrypt_credentials(["list", "not", "dict"])

    def test_decrypt_rejects_non_string(self):
        """Test that decrypt_credentials rejects non-string inputs."""
        encryptor = CredentialEncryptor("test-key")

        with pytest.raises(TypeError):
            encryptor.decrypt_credentials({"not": "a string"})

    def test_mask_credentials_hides_sensitive_fields(self):
        """Test that mask_credentials properly masks sensitive fields."""
        credentials = {
            "api_key": "sk_live_abc123def456",
            "client_secret": "secret_xyz789",
            "password": "mypassword123",
            "access_token": "token_abc123xyz",
            "service_url": "https://api.example.com",
            "username": "testuser"
        }

        masked = mask_credentials(credentials)

        # Sensitive fields should be masked
        assert masked["api_key"] != "sk_live_abc123def456"
        assert masked["client_secret"] != "secret_xyz789"
        assert masked["password"] != "mypassword123"
        assert masked["access_token"] != "token_abc123xyz"

        # Non-sensitive fields should be preserved
        assert masked["service_url"] == "https://api.example.com"
        assert masked["username"] == "testuser"

    def test_mask_credentials_short_values(self):
        """Test masking of short sensitive values."""
        credentials = {
            "api_key": "ab",
            "secret": "xyz"
        }

        masked = mask_credentials(credentials)

        # Short values should be masked to ****
        assert masked["api_key"] == "****"
        assert masked["secret"] == "****"

    def test_mask_credentials_empty_dict(self):
        """Test masking of empty credentials dictionary."""
        masked = mask_credentials({})
        assert masked == {}

    def test_mask_credentials_non_dict(self):
        """Test masking of non-dict input."""
        masked = mask_credentials("not a dict")
        assert masked == {}


class TestGlobalEncryptor:
    """Tests for global encryptor functions."""

    def test_encrypt_decrypt_functions(self):
        """Test convenience functions for encryption."""
        data = {"api_key": "test123"}

        encrypted = encrypt_credentials(data, secret_key="test-key")
        decrypted = decrypt_credentials(encrypted, secret_key="test-key")

        assert decrypted == data

    def test_mask_credentials_function(self):
        """Test convenience function for masking."""
        data = {
            "api_key": "sk_live_test123",
            "service_url": "https://api.test.com"
        }

        masked = mask_credentials(data)

        assert masked["api_key"] != "sk_live_test123"
        assert masked["service_url"] == "https://api.test.com"


class TestEncryptionIntegration:
    """Integration tests for encryption in the context of connector usage."""

    def test_realistic_connector_credentials(self):
        """Test encryption of realistic connector credentials."""
        # Simulate Stripe connector credentials
        stripe_creds = {
            "api_key": "sk_live_51234567890abcdefghijklmnop",
            "restricted_api_key": "rk_live_1234567890abcdefghijk",
            "webhook_secret": "whsec_1234567890abcdefghijklmnop"
        }

        encrypted = encrypt_credentials(stripe_creds, secret_key="prod-secret-key")
        decrypted = decrypt_credentials(encrypted, secret_key="prod-secret-key")

        assert decrypted == stripe_creds

    def test_oauth_credentials(self):
        """Test encryption of OAuth credentials."""
        oauth_creds = {
            "client_id": "client_abc123def456",
            "client_secret": "secret_xyz789uvw012",
            "access_token": "access_token_abc123def456",
            "refresh_token": "refresh_token_xyz789uvw012",
            "token_type": "Bearer",
            "expires_in": 3600,
            "expires_at": 1234567890
        }

        encrypted = encrypt_credentials(oauth_creds)
        decrypted = decrypt_credentials(encrypted)

        assert decrypted == oauth_creds

    def test_database_storage_simulation(self):
        """Test simulating database storage and retrieval."""
        credentials = {
            "username": "admin",
            "password": "secure_password_123",
            "host": "db.example.com",
            "port": 5432,
            "database": "production"
        }

        # Simulate storing in database
        encrypted_for_db = encrypt_credentials(credentials, secret_key="db-secret")
        db_value = encrypted_for_db  # This would be stored in DB

        # Simulate retrieving from database
        retrieved_from_db = db_value
        credentials_from_db = decrypt_credentials(retrieved_from_db, secret_key="db-secret")

        assert credentials_from_db == credentials

    def test_multiple_credentials_in_metadata(self):
        """Test encryption of multiple provider credentials in metadata."""
        metadata = {
            "connectors": {
                "stripe": {
                    "connected": True,
                    "credentials": None,  # Will be encrypted
                    "settings": {}
                },
                "quickbooks": {
                    "connected": True,
                    "credentials": None,  # Will be encrypted
                    "settings": {}
                }
            }
        }

        stripe_creds = {"api_key": "sk_live_123"}
        qb_creds = {"realm_id": "abc123", "access_token": "token_xyz"}

        # Encrypt individual credential sets
        metadata["connectors"]["stripe"]["credentials"] = encrypt_credentials(stripe_creds)
        metadata["connectors"]["quickbooks"]["credentials"] = encrypt_credentials(qb_creds)

        # Simulate retrieval
        retrieved_stripe = decrypt_credentials(metadata["connectors"]["stripe"]["credentials"])
        retrieved_qb = decrypt_credentials(metadata["connectors"]["quickbooks"]["credentials"])

        assert retrieved_stripe == stripe_creds
        assert retrieved_qb == qb_creds


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
