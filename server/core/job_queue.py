import json
import uuid
import time
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum

from server.core.redis_client import get_redis

logger = logging.getLogger(__name__)

PREFIX = "fc:queue:"


class JobStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class QueueName(str, Enum):
    SIMULATION = "simulation"
    CONNECTOR_SYNC = "connector_sync"
    AI_AGENT = "ai_agent"
    NOTIFICATION = "notification"


@dataclass
class Job:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    queue: str = ""
    type: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    status: str = JobStatus.PENDING.value
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    priority: int = 0

    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)

    @classmethod
    def from_json(cls, data: str) -> "Job":
        d = json.loads(data)
        return cls(**d)


def enqueue(queue: QueueName, job_type: str, payload: Dict[str, Any], priority: int = 0) -> Job:
    job = Job(
        queue=queue.value,
        type=job_type,
        payload=payload,
        priority=priority,
    )
    r = get_redis()
    queue_key = PREFIX + queue.value

    r.lpush(queue_key, job.to_json())

    status_key = PREFIX + "status:" + job.id
    r.setex(status_key, 3600, job.to_json())

    logger.info(f"Enqueued job {job.id} to {queue.value} (type={job_type})")
    return job


def dequeue(queue: QueueName, timeout: int = 5) -> Optional[Job]:
    r = get_redis()
    queue_key = PREFIX + queue.value

    result = r.brpop(queue_key, timeout=timeout)
    if result is None:
        return None

    _, job_data = result
    job = Job.from_json(job_data)
    job.status = JobStatus.RUNNING.value
    job.started_at = time.time()

    status_key = PREFIX + "status:" + job.id
    r.setex(status_key, 3600, job.to_json())

    return job


def complete_job(job: Job, result: Optional[Dict[str, Any]] = None):
    job.status = JobStatus.COMPLETED.value
    job.completed_at = time.time()
    job.result = result

    r = get_redis()
    status_key = PREFIX + "status:" + job.id
    r.setex(status_key, 3600, job.to_json())


def fail_job(job: Job, error: str):
    job.status = JobStatus.FAILED.value
    job.completed_at = time.time()
    job.error = error

    r = get_redis()
    status_key = PREFIX + "status:" + job.id
    r.setex(status_key, 3600, job.to_json())


def get_job_status(job_id: str) -> Optional[Job]:
    r = get_redis()
    status_key = PREFIX + "status:" + job_id
    data = r.get(status_key)
    if data:
        return Job.from_json(data)
    return None


def get_queue_length(queue: QueueName) -> int:
    r = get_redis()
    return r.llen(PREFIX + queue.value)


def get_queue_stats() -> Dict[str, int]:
    return {q.value: get_queue_length(q) for q in QueueName}
