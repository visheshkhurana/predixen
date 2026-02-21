"""
Migration utilities for encrypting existing plaintext connector credentials.

This module provides functions to:
1. Scan the database for plaintext credentials
2. Encrypt existing plaintext credentials in-place
3. Verify encryption status

This should be run as a one-time migration after deploying the encryption system.
"""

import logging
from typing import Dict, Tuple, List
from sqlalchemy.orm import Session

from server.core.encryption import encrypt_credentials, decrypt_credentials
from server.models.company import Company

logger = logging.getLogger(__name__)


def scan_plaintext_credentials(db: Session) -> List[Dict]:
    """
    Scan all companies for plaintext (unencrypted) connector credentials.

    Detects credentials that are stored as dictionaries rather than encrypted
    strings in the company metadata.

    Args:
        db: SQLAlchemy database session

    Returns:
        list: List of companies with plaintext credentials
            [
                {
                    "company_id": int,
                    "company_name": str,
                    "provider_ids": [str],  # List of providers with plaintext creds
                }
            ]
    """
    results = []

    companies = db.query(Company).all()

    for company in companies:
        metadata = company.metadata_json or {}
        connectors = metadata.get("connectors", {})

        plaintext_providers = []

        for provider_id, config in connectors.items():
            if not isinstance(config, dict):
                continue

            credentials = config.get("credentials")

            # Plaintext credentials are stored as dicts, encrypted ones as strings
            if isinstance(credentials, dict) and credentials:
                plaintext_providers.append(provider_id)

        if plaintext_providers:
            results.append(
                {
                    "company_id": company.id,
                    "company_name": company.name,
                    "provider_ids": plaintext_providers,
                }
            )

    return results


def migrate_plaintext_credentials(db: Session, dry_run: bool = True) -> Tuple[int, int, List[str]]:
    """
    Encrypt all plaintext connector credentials in the database.

    This is a one-time migration function that should be run after deploying
    the encryption system.

    Args:
        db: SQLAlchemy database session
        dry_run: If True, scan and report without making changes. If False, encrypt credentials.

    Returns:
        tuple: (total_encrypted, total_errors, error_messages)
            - total_encrypted: Number of connector credentials successfully encrypted
            - total_errors: Number of errors encountered
            - error_messages: List of error descriptions for debugging
    """
    total_encrypted = 0
    total_errors = 0
    error_messages = []

    plaintext_findings = scan_plaintext_credentials(db)

    if dry_run:
        logger.info(f"DRY RUN: Found {len(plaintext_findings)} companies with plaintext credentials")
        for finding in plaintext_findings:
            logger.info(
                f"  - Company {finding['company_id']} ({finding['company_name']}): "
                f"{', '.join(finding['provider_ids'])}"
            )
        return total_encrypted, total_errors, error_messages

    # Perform actual encryption
    for finding in plaintext_findings:
        company_id = finding["company_id"]
        company = db.query(Company).filter(Company.id == company_id).first()

        if not company:
            error_msg = f"Company {company_id} not found during migration"
            logger.error(error_msg)
            error_messages.append(error_msg)
            total_errors += 1
            continue

        metadata = company.metadata_json or {}
        connectors = metadata.get("connectors", {})

        for provider_id in finding["provider_ids"]:
            if provider_id not in connectors:
                continue

            config = connectors[provider_id]
            credentials = config.get("credentials")

            # Skip if already encrypted or empty
            if not isinstance(credentials, dict):
                continue

            try:
                # Encrypt the plaintext credentials
                encrypted = encrypt_credentials(credentials)

                # Update the config with encrypted credentials
                config["credentials"] = encrypted
                config["encrypted"] = True
                config["migration_encrypted_at"] = __import__("datetime").datetime.utcnow().isoformat()

                logger.info(
                    f"Encrypted credentials for company {company_id}, provider {provider_id}"
                )
                total_encrypted += 1

            except Exception as e:
                error_msg = (
                    f"Failed to encrypt credentials for company {company_id}, "
                    f"provider {provider_id}: {str(e)}"
                )
                logger.error(error_msg)
                error_messages.append(error_msg)
                total_errors += 1

        # Save updated metadata
        metadata["connectors"] = connectors
        company.metadata_json = metadata

    # Commit all changes
    if total_encrypted > 0 or total_errors == 0:
        try:
            db.commit()
            logger.info(f"Migration complete: {total_encrypted} credentials encrypted")
        except Exception as e:
            db.rollback()
            error_msg = f"Failed to commit migration changes: {str(e)}"
            logger.error(error_msg)
            error_messages.append(error_msg)
            total_errors += 1

    return total_encrypted, total_errors, error_messages


def verify_encryption_status(db: Session) -> Dict:
    """
    Verify the encryption status of all connector credentials in the database.

    Returns a summary of the encryption state across the database.

    Args:
        db: SQLAlchemy database session

    Returns:
        dict: Status report
            {
                "total_companies": int,
                "companies_with_connectors": int,
                "total_connectors": int,
                "encrypted_connectors": int,
                "plaintext_connectors": int,
                "unknown_format": int,
                "migration_needed": bool,
            }
    """
    report = {
        "total_companies": 0,
        "companies_with_connectors": 0,
        "total_connectors": 0,
        "encrypted_connectors": 0,
        "plaintext_connectors": 0,
        "unknown_format": 0,
        "migration_needed": False,
    }

    companies = db.query(Company).all()
    report["total_companies"] = len(companies)

    for company in companies:
        metadata = company.metadata_json or {}
        connectors = metadata.get("connectors", {})

        if not connectors:
            continue

        report["companies_with_connectors"] += 1

        for provider_id, config in connectors.items():
            if not isinstance(config, dict):
                continue

            credentials = config.get("credentials")

            # Skip if no credentials
            if not credentials:
                continue

            report["total_connectors"] += 1

            # Check if encrypted (string) or plaintext (dict)
            if isinstance(credentials, str):
                report["encrypted_connectors"] += 1
            elif isinstance(credentials, dict):
                report["plaintext_connectors"] += 1
            else:
                report["unknown_format"] += 1

    # Migration is needed if there are any plaintext connectors
    report["migration_needed"] = report["plaintext_connectors"] > 0

    return report


async def auto_migrate_on_startup(db: Session) -> None:
    """
    Automatically migrate plaintext credentials on application startup if needed.

    This function checks if plaintext credentials exist and offers to migrate them.
    In production, you may want to handle this differently (e.g., log a warning).

    Args:
        db: SQLAlchemy database session
    """
    status = verify_encryption_status(db)

    if status["migration_needed"]:
        logger.warning(
            f"Found {status['plaintext_connectors']} plaintext credentials. "
            f"Running automatic migration..."
        )

        total_encrypted, total_errors, errors = migrate_plaintext_credentials(db, dry_run=False)

        if total_errors > 0:
            logger.error(f"Migration completed with {total_errors} errors:")
            for error in errors:
                logger.error(f"  - {error}")
        else:
            logger.info(f"Successfully encrypted {total_encrypted} credentials")
    else:
        logger.debug(
            f"Encryption status: {status['encrypted_connectors']} encrypted, "
            f"0 plaintext, 0 errors"
        )
