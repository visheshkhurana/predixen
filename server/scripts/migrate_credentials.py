#!/usr/bin/env python3
"""
CLI script to encrypt existing plaintext connector credentials.

Usage:
    python server/scripts/migrate_credentials.py --status              # Check current status
    python server/scripts/migrate_credentials.py --dry-run             # Preview what will be encrypted
    python server/scripts/migrate_credentials.py --migrate             # Perform actual migration
    python server/scripts/migrate_credentials.py --verify              # Verify encryption status

This script should be run ONCE after deploying the encryption system to migrate
all existing plaintext credentials to encrypted form.
"""

import sys
import os
import argparse
import logging

# Setup path to import server modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from server.core.db import SessionLocal
from server.core.credential_migration import (
    verify_encryption_status,
    migrate_plaintext_credentials,
    scan_plaintext_credentials,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def show_status():
    """Display current encryption status."""
    db = SessionLocal()
    try:
        status = verify_encryption_status(db)

        print("\n" + "=" * 60)
        print("CREDENTIAL ENCRYPTION STATUS")
        print("=" * 60)
        print(f"Total Companies: {status['total_companies']}")
        print(f"Companies with Connectors: {status['companies_with_connectors']}")
        print(f"Total Connector Credentials: {status['total_connectors']}")
        print(f"  - Encrypted: {status['encrypted_connectors']}")
        print(f"  - Plaintext: {status['plaintext_connectors']}")
        print(f"  - Unknown Format: {status['unknown_format']}")
        print(f"\nMigration Needed: {'YES' if status['migration_needed'] else 'NO'}")
        print("=" * 60 + "\n")

        if status["plaintext_connectors"] > 0:
            print("Companies with plaintext credentials:")
            findings = scan_plaintext_credentials(db)
            for finding in findings:
                print(
                    f"  - {finding['company_name']} (ID: {finding['company_id']}): "
                    f"{', '.join(finding['provider_ids'])}"
                )
            print()

    finally:
        db.close()


def show_dry_run():
    """Preview what will be encrypted without making changes."""
    print("\nRunning DRY RUN (no changes will be made)...\n")

    db = SessionLocal()
    try:
        total_encrypted, total_errors, errors = migrate_plaintext_credentials(db, dry_run=True)

        print(f"\nDRY RUN RESULTS:")
        print(f"  Credentials to be encrypted: {total_encrypted}")
        if errors:
            print(f"  Potential errors: {total_errors}")
            for error in errors:
                print(f"    - {error}")
        print()

    finally:
        db.close()


def perform_migration():
    """Perform actual migration."""
    print("\n" + "!" * 60)
    print("PERFORMING ACTUAL MIGRATION")
    print("!" * 60 + "\n")

    confirm = input("This will encrypt all plaintext credentials. Continue? (yes/no): ")
    if confirm.lower() != "yes":
        print("Migration cancelled.")
        return

    db = SessionLocal()
    try:
        total_encrypted, total_errors, errors = migrate_plaintext_credentials(
            db, dry_run=False
        )

        print(f"\nMIGRATION RESULTS:")
        print(f"  Successfully encrypted: {total_encrypted}")
        print(f"  Errors encountered: {total_errors}")

        if errors:
            print("\nErrors:")
            for error in errors:
                print(f"  - {error}")

        if total_errors == 0:
            print("\n✓ Migration completed successfully!")
        else:
            print(f"\n⚠ Migration completed with {total_errors} error(s)")

        print()

    finally:
        db.close()


def verify():
    """Verify encryption status."""
    show_status()


def main():
    parser = argparse.ArgumentParser(
        description="Migrate plaintext connector credentials to encrypted form"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current encryption status"
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without changes")
    parser.add_argument("--migrate", action="store_true", help="Perform actual migration")
    parser.add_argument("--verify", action="store_true", help="Verify encryption status")

    args = parser.parse_args()

    # Default to status if no arguments
    if not any([args.status, args.dry_run, args.migrate, args.verify]):
        args.status = True

    if args.status:
        show_status()
    elif args.dry_run:
        show_dry_run()
    elif args.migrate:
        perform_migration()
    elif args.verify:
        verify()


if __name__ == "__main__":
    main()
