"""
Connector Sync Queue Manager — database-backed async job queue
for connector sync operations with priority scheduling, retry logic,
and rate limiting per provider.
"""
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class SyncPriority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


class SyncJobStatus(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    RATE_LIMITED = "RATE_LIMITED"


@dataclass
class SyncJob:
    job_id: str
    company_id: int
    provider_id: str
    priority: SyncPriority
    status: SyncJobStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "company_id": self.company_id,
            "provider_id": self.provider_id,
            "priority": self.priority.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


PROVIDER_RATE_LIMITS: Dict[str, Dict[str, Any]] = {
    "stripe": {"requests_per_minute": 25, "min_interval_seconds": 3},
    "quickbooks": {"requests_per_minute": 10, "min_interval_seconds": 6},
    "gusto": {"requests_per_minute": 15, "min_interval_seconds": 4},
    "xero": {"requests_per_minute": 10, "min_interval_seconds": 6},
    "hubspot": {"requests_per_minute": 10, "min_interval_seconds": 6},
    "salesforce": {"requests_per_minute": 15, "min_interval_seconds": 4},
    "plaid": {"requests_per_minute": 20, "min_interval_seconds": 3},
    "default": {"requests_per_minute": 10, "min_interval_seconds": 6},
}


RETRY_BACKOFF_SECONDS = [30, 120, 600]


class ConnectorSyncQueue:
    """
    Database-backed async queue for connector sync operations.
    Supports priority scheduling, rate limiting, and automatic retries.
    """

    def __init__(self):
        self._queue: List[SyncJob] = []
        self._provider_last_run: Dict[str, datetime] = {}
        self._provider_run_count: Dict[str, List[datetime]] = {}

    def enqueue(
        self,
        company_id: int,
        provider_id: str,
        priority: SyncPriority = SyncPriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SyncJob:
        """Add a sync job to the queue."""
        existing = self._find_pending_job(company_id, provider_id)
        if existing:
            if priority.value < existing.priority.value:
                existing.priority = priority
                logger.info(
                    f"Upgraded priority for existing job {existing.job_id} "
                    f"to {priority.name}"
                )
            return existing

        job = SyncJob(
            job_id=str(uuid.uuid4()),
            company_id=company_id,
            provider_id=provider_id,
            priority=priority,
            status=SyncJobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            metadata=metadata or {},
        )

        self._queue.append(job)
        self._queue.sort(key=lambda j: (j.priority.value, j.created_at))

        logger.info(
            f"Enqueued sync job {job.job_id}: {provider_id} for company {company_id} "
            f"(priority: {priority.name}, queue size: {len(self._queue)})"
        )

        return job

    def dequeue(self) -> Optional[SyncJob]:
        """Get the next job to process, respecting rate limits."""
        now = datetime.now(timezone.utc)

        for job in self._queue:
            if job.status == SyncJobStatus.RATE_LIMITED:
                job.status = SyncJobStatus.PENDING

        for job in self._queue:
            if job.status != SyncJobStatus.PENDING:
                continue

            if not self._check_rate_limit(job.provider_id, now):
                continue

            if job.retry_count > 0:
                backoff_idx = min(job.retry_count - 1, len(RETRY_BACKOFF_SECONDS) - 1)
                backoff = RETRY_BACKOFF_SECONDS[backoff_idx]
                if job.completed_at and (now - job.completed_at).total_seconds() < backoff:
                    continue

            job.status = SyncJobStatus.RUNNING
            job.started_at = now
            self._record_provider_run(job.provider_id, now)

            logger.info(f"Dequeued job {job.job_id}: {job.provider_id}")
            return job

        return None

    def complete(
        self,
        job_id: str,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[SyncJob]:
        """Mark a job as completed."""
        job = self._find_job(job_id)
        if not job:
            return None

        job.status = SyncJobStatus.COMPLETED
        job.completed_at = datetime.now(timezone.utc)
        job.result = result

        logger.info(f"Completed job {job_id}: {job.provider_id}")
        return job

    def fail(
        self,
        job_id: str,
        error_message: str,
    ) -> Optional[SyncJob]:
        """Mark a job as failed. Will retry if under max retries."""
        job = self._find_job(job_id)
        if not job:
            return None

        job.error_message = error_message
        job.completed_at = datetime.now(timezone.utc)

        if job.retry_count < job.max_retries:
            job.retry_count += 1
            job.status = SyncJobStatus.PENDING
            logger.info(
                f"Job {job_id} failed, scheduling retry {job.retry_count}/{job.max_retries}: "
                f"{error_message}"
            )
        else:
            job.status = SyncJobStatus.FAILED
            logger.error(
                f"Job {job_id} permanently failed after {job.max_retries} retries: "
                f"{error_message}"
            )

        return job

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status."""
        status_counts = {}
        for job in self._queue:
            s = job.status.value
            status_counts[s] = status_counts.get(s, 0) + 1

        return {
            "total_jobs": len(self._queue),
            "status_breakdown": status_counts,
            "pending": status_counts.get("PENDING", 0),
            "running": status_counts.get("RUNNING", 0),
            "completed": status_counts.get("COMPLETED", 0),
            "failed": status_counts.get("FAILED", 0),
        }

    def get_company_jobs(self, company_id: int) -> List[Dict[str, Any]]:
        """Get all jobs for a specific company."""
        return [
            job.to_dict()
            for job in self._queue
            if job.company_id == company_id
        ]

    def cleanup_completed(self, max_age_hours: int = 24) -> int:
        """Remove completed/failed jobs older than max_age_hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        before = len(self._queue)
        self._queue = [
            job
            for job in self._queue
            if job.status not in (SyncJobStatus.COMPLETED, SyncJobStatus.FAILED)
            or (job.completed_at and job.completed_at > cutoff)
        ]
        removed = before - len(self._queue)
        if removed:
            logger.info(f"Cleaned up {removed} old jobs from queue")
        return removed

    def _find_job(self, job_id: str) -> Optional[SyncJob]:
        for job in self._queue:
            if job.job_id == job_id:
                return job
        return None

    def _find_pending_job(
        self, company_id: int, provider_id: str
    ) -> Optional[SyncJob]:
        for job in self._queue:
            if (
                job.company_id == company_id
                and job.provider_id == provider_id
                and job.status in (SyncJobStatus.PENDING, SyncJobStatus.RUNNING)
            ):
                return job
        return None

    def _check_rate_limit(self, provider_id: str, now: datetime) -> bool:
        limits = PROVIDER_RATE_LIMITS.get(
            provider_id, PROVIDER_RATE_LIMITS["default"]
        )
        min_interval = limits["min_interval_seconds"]
        max_rpm = limits["requests_per_minute"]

        last_run = self._provider_last_run.get(provider_id)
        if last_run and (now - last_run).total_seconds() < min_interval:
            return False

        runs = self._provider_run_count.get(provider_id, [])
        one_minute_ago = now - timedelta(minutes=1)
        recent_runs = [r for r in runs if r > one_minute_ago]
        self._provider_run_count[provider_id] = recent_runs

        if len(recent_runs) >= max_rpm:
            return False

        return True

    def _record_provider_run(self, provider_id: str, now: datetime):
        self._provider_last_run[provider_id] = now
        if provider_id not in self._provider_run_count:
            self._provider_run_count[provider_id] = []
        self._provider_run_count[provider_id].append(now)


sync_queue = ConnectorSyncQueue()
