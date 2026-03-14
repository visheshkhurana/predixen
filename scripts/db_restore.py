#!/usr/bin/env python3
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("db_restore")

DATABASE_URL = os.getenv("DATABASE_URL", "")
BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/backups")


def restore_backup(backup_file: str):
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    if not os.path.isabs(backup_file):
        backup_file = os.path.join(BACKUP_DIR, backup_file)

    backup_file = os.path.realpath(backup_file)
    if not backup_file.startswith(os.path.realpath(BACKUP_DIR)):
        logger.error("Backup file must be inside the backup directory")
        sys.exit(1)

    if not os.path.exists(backup_file):
        logger.error(f"Backup file not found: {backup_file}")
        sys.exit(1)

    logger.info(f"Restoring from {backup_file}")
    logger.warning("This will overwrite the current database!")

    try:
        gunzip = subprocess.Popen(
            ["gunzip", "-c", backup_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        psql = subprocess.Popen(
            ["psql", DATABASE_URL],
            stdin=gunzip.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        gunzip.stdout.close()
        _, stderr = psql.communicate(timeout=600)

        if psql.returncode != 0:
            logger.error(f"Restore failed: {stderr.decode()}")
            sys.exit(1)

        logger.info("Restore completed successfully")

    except subprocess.TimeoutExpired:
        logger.error("Restore timed out after 10 minutes")
        sys.exit(1)


def list_backups():
    if not os.path.exists(BACKUP_DIR):
        logger.info("No backup directory found")
        return

    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith("founderconsole_") and f.endswith(".sql.gz")
    ])

    if not backups:
        logger.info("No backups found")
        return

    logger.info(f"Available backups ({len(backups)}):")
    for b in backups:
        size = os.path.getsize(os.path.join(BACKUP_DIR, b))
        logger.info(f"  {b} ({size / 1024 / 1024:.1f} MB)")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python db_restore.py <backup_file>")
        print("       python db_restore.py --list")
        sys.exit(1)

    if sys.argv[1] == "--list":
        list_backups()
    else:
        restore_backup(sys.argv[1])
