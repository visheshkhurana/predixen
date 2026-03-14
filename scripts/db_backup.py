#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("db_backup")

BACKUP_DIR = os.getenv("BACKUP_DIR", "/tmp/backups")
DATABASE_URL = os.getenv("DATABASE_URL", "")
MAX_BACKUPS = int(os.getenv("MAX_BACKUPS", "7"))


def run_backup():
    if not DATABASE_URL:
        logger.error("DATABASE_URL not set")
        sys.exit(1)

    os.makedirs(BACKUP_DIR, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"founderconsole_{timestamp}.sql.gz"
    filepath = os.path.join(BACKUP_DIR, filename)

    logger.info(f"Starting backup to {filepath}")

    try:
        pg_dump = subprocess.Popen(
            ["pg_dump", DATABASE_URL],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        gzip_proc = subprocess.Popen(
            ["gzip"],
            stdin=pg_dump.stdout,
            stdout=open(filepath, "wb"),
            stderr=subprocess.PIPE,
        )
        pg_dump.stdout.close()
        gzip_proc.communicate(timeout=600)

        if pg_dump.wait() != 0:
            logger.error(f"pg_dump failed: {pg_dump.stderr.read().decode()}")
            sys.exit(1)

        size = os.path.getsize(filepath)
        logger.info(f"Backup completed: {filename} ({size / 1024 / 1024:.1f} MB)")

        _cleanup_old_backups()

    except subprocess.TimeoutExpired:
        logger.error("Backup timed out after 10 minutes")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Backup error: {e}")
        sys.exit(1)


def _cleanup_old_backups():
    backups = sorted([
        f for f in os.listdir(BACKUP_DIR)
        if f.startswith("founderconsole_") and f.endswith(".sql.gz")
    ])

    while len(backups) > MAX_BACKUPS:
        old = backups.pop(0)
        path = os.path.join(BACKUP_DIR, old)
        os.remove(path)
        logger.info(f"Removed old backup: {old}")


if __name__ == "__main__":
    run_backup()
