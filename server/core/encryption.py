"""
Secure encryption module for storing sensitive connector credentials.

Uses Fernet symmetric encryption from the cryptography library with
a key derived from the application's SECRET_KEY using PBKDF2.

This module ensures that API keys, tokens, and other sensitive
credentials are encrypted at rest in the database and never stored
as plaintext.
"""

import json
import os
import logging
from typing import Dict, Any

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import base64

logger = logging.getLogger(__name__)


class CredentialEncryptor:
    """Handles encryption and decryption of connector credentials."""

    # Derivation salt - configurable per installation via env var
    # Default salt is for development; production should set ENCRYPTION_SALT env var
    _SALT = os.getenv("ENCRYPTION_SALT", "founderconsole-credential-salt-v1").encode("utf-8")

    def __init__(self, secret_key: str):
        """
        Initialize the encryptor with a secret key.

        Args:
            secret_key: The master secret key (typically SESSION_SECRET from config)
        """
        self.secret_key = secret_key
        self._cipher = self._derive_cipher()

    def _derive_cipher(self) -> Fernet:
        """
        Derive a Fernet cipher from the secret key using PBKDF2.

        Uses PBKDF2 with SHA256 to derive a 32-byte key suitable for Fernet.
        The derived key is base64-encoded as required by Fernet.

        Returns:
            Fernet: Initialized Fernet cipher for encryption/decryption
        """
        # Ensure secret_key is bytes
        if isinstance(self.secret_key, str):
            secret_bytes = self.secret_key.encode("utf-8")
        else:
            secret_bytes = self.secret_key

        # Derive 32-byte key from secret using PBKDF2
        # 100,000 iterations is the Fernet recommendation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self._SALT,
            iterations=100_000,
            backend=default_backend(),
        )

        derived_key = kdf.derive(secret_bytes)

        # Fernet requires base64-encoded 32-byte key
        encoded_key = base64.urlsafe_b64encode(derived_key)

        return Fernet(encoded_key)

    def encrypt_credentials(self, credentials: Dict[str, Any]) -> str:
        """
        Encrypt credential dictionary to a single encrypted string.

        Args:
            credentials: Dictionary containing API keys, tokens, secrets, etc.

        Returns:
            str: Encrypted credentials as a URL-safe base64 string

        Raises:
            TypeError: If credentials is not a dictionary
            Exception: If encryption fails
        """
        if not isinstance(credentials, dict):
            raise TypeError(f"credentials must be a dict, got {type(credentials)}")

        try:
            # Serialize credentials to JSON
            json_str = json.dumps(credentials, separators=(",", ":"), sort_keys=True)
            json_bytes = json_str.encode("utf-8")

            # Encrypt using Fernet
            encrypted = self._cipher.encrypt(json_bytes)

            # Return as UTF-8 string (Fernet returns bytes)
            return encrypted.decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to encrypt credentials: {e}")
            raise

    def decrypt_credentials(self, encrypted: str) -> Dict[str, Any]:
        """
        Decrypt an encrypted credential string back to dictionary.

        Args:
            encrypted: Encrypted credentials string from encrypt_credentials()

        Returns:
            dict: Decrypted credentials dictionary

        Raises:
            ValueError: If decryption fails (tampered data, wrong key, etc.)
            Exception: If decryption fails for other reasons
        """
        if not isinstance(encrypted, str):
            raise TypeError(f"encrypted must be a string, got {type(encrypted)}")

        try:
            # Convert string back to bytes for Fernet
            encrypted_bytes = encrypted.encode("utf-8")

            # Decrypt using Fernet
            decrypted = self._cipher.decrypt(encrypted_bytes)

            # Deserialize JSON
            json_str = decrypted.decode("utf-8")
            credentials = json.loads(json_str)

            return credentials

        except Exception as e:
            logger.error(f"Failed to decrypt credentials: {e}")
            raise ValueError(f"Failed to decrypt credentials: Invalid data or wrong key") from e

    @staticmethod
    def mask_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a masked copy of credentials for logging/display purposes.

        Sensitive fields (api_key, token, secret, password, access_token, etc.)
        are masked, while non-sensitive metadata is preserved.

        Args:
            credentials: Original credentials dictionary

        Returns:
            dict: Masked credentials with sensitive values hidden
        """
        if not isinstance(credentials, dict):
            return {}

        # Fields that should be masked (case-insensitive)
        sensitive_fields = {
            "api_key",
            "apikey",
            "api_secret",
            "secret",
            "secret_key",
            "token",
            "access_token",
            "refresh_token",
            "password",
            "passwd",
            "bearer",
            "auth_token",
            "oauth_token",
            "private_key",
            "client_secret",
            "signing_key",
        }

        masked = {}
        for key, value in credentials.items():
            key_lower = key.lower()

            # Check if this is a sensitive field
            if key_lower in sensitive_fields or any(
                sensitive in key_lower for sensitive in sensitive_fields
            ):
                # Mask sensitive values
                if isinstance(value, str):
                    if len(value) > 4:
                        masked[key] = f"{value[:2]}...{value[-2:]}"
                    else:
                        masked[key] = "****"
                else:
                    masked[key] = "****"
            else:
                # Preserve non-sensitive values (like service_url, environment, etc.)
                masked[key] = value

        return masked


# Global encryptor instance (lazy-loaded)
_encryptor: CredentialEncryptor = None
_current_secret_key: str = None


def get_encryptor(secret_key: str = None) -> CredentialEncryptor:
    """
    Get or create the global credential encryptor.

    Args:
        secret_key: Optional secret key. If not provided, uses SESSION_SECRET from config.

    Returns:
        CredentialEncryptor: Initialized encryptor instance
    """
    global _encryptor, _current_secret_key

    if secret_key is None:
        # Import here to avoid circular imports
        from server.core.config import get_settings

        settings = get_settings()
        secret_key = settings.SECRET_KEY

    # Create new encryptor if none exists or if secret_key changed
    if _encryptor is None or _current_secret_key != secret_key:
        _encryptor = CredentialEncryptor(secret_key)
        _current_secret_key = secret_key

    return _encryptor


def encrypt_credentials(credentials: Dict[str, Any], secret_key: str = None) -> str:
    """
    Convenience function to encrypt credentials using the global encryptor.

    Args:
        credentials: Dictionary of credentials to encrypt
        secret_key: Optional secret key

    Returns:
        str: Encrypted credentials string
    """
    encryptor = get_encryptor(secret_key)
    return encryptor.encrypt_credentials(credentials)


def decrypt_credentials(encrypted: str, secret_key: str = None) -> Dict[str, Any]:
    """
    Convenience function to decrypt credentials using the global encryptor.

    Args:
        encrypted: Encrypted credentials string
        secret_key: Optional secret key

    Returns:
        dict: Decrypted credentials dictionary
    """
    encryptor = get_encryptor(secret_key)
    return encryptor.decrypt_credentials(encrypted)


def mask_credentials(credentials: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to mask credentials for logging.

    Args:
        credentials: Dictionary of credentials to mask

    Returns:
        dict: Masked credentials dictionary
    """
    return CredentialEncryptor.mask_credentials(credentials)
