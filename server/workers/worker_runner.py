import os
import sys
import time
import signal
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Callable, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("worker_runner")

from server.core.job_queue import dequeue, complete_job, fail_job, QueueName, Job

MAX_CONCURRENT = int(os.environ.get("WORKER_MAX_CONCURRENT", "4"))
_shutdown = threading.Event()

_handlers: Dict[str, Callable] = {}


def register_handler(job_type: str, handler: Callable):
    _handlers[job_type] = handler
    logger.info(f"Registered handler for job type: {job_type}")


def _process_job(job: Job):
    handler = _handlers.get(job.type)
    if not handler:
        fail_job(job, f"No handler registered for job type: {job.type}")
        return

    try:
        result = handler(job.payload)
        complete_job(job, result)
        elapsed = time.time() - (job.started_at or job.created_at)
        logger.info(f"Job {job.id} ({job.type}) completed in {elapsed:.1f}s")
    except Exception as e:
        logger.error(f"Job {job.id} ({job.type}) failed: {e}", exc_info=True)
        fail_job(job, str(e)[:500])


def run_worker(queues: list[QueueName]):
    logger.info("=" * 60)
    logger.info("FounderConsole Worker Runner starting")
    logger.info(f"  Queues: {[q.value for q in queues]}")
    logger.info(f"  Max concurrent: {MAX_CONCURRENT}")
    logger.info(f"  Registered handlers: {list(_handlers.keys())}")
    logger.info("=" * 60)

    executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT, thread_name_prefix="worker")
    active_futures: Dict[str, Future] = {}

    def _cleanup():
        done = [jid for jid, f in active_futures.items() if f.done()]
        for jid in done:
            future = active_futures.pop(jid)
            exc = future.exception()
            if exc:
                logger.error(f"Job {jid} thread raised: {exc}")

    try:
        while not _shutdown.is_set():
            _cleanup()

            if len(active_futures) >= MAX_CONCURRENT:
                _shutdown.wait(timeout=0.5)
                continue

            for queue in queues:
                if len(active_futures) >= MAX_CONCURRENT:
                    break

                job = dequeue(queue, timeout=1)
                if job:
                    logger.info(f"Claimed job {job.id} from {queue.value} (type={job.type})")
                    future = executor.submit(_process_job, job)
                    active_futures[job.id] = future

            if not active_futures:
                _shutdown.wait(timeout=2.0)
    except KeyboardInterrupt:
        pass
    finally:
        logger.info("Worker shutting down, waiting for active jobs...")
        executor.shutdown(wait=True, cancel_futures=False)
        logger.info("Worker Runner stopped")


def _handle_signal(signum, frame):
    logger.info(f"Received signal {signum}, initiating shutdown...")
    _shutdown.set()


def _register_all_handlers():
    from server.workers.handlers.simulation_handler import handle_simulation
    from server.workers.handlers.connector_handler import handle_connector_sync
    from server.workers.handlers.forecast_handler import handle_forecast

    register_handler("simulation.run", handle_simulation)
    register_handler("simulation.sensitivity", handle_simulation)
    register_handler("connector.sync", handle_connector_sync)
    register_handler("forecast.run", handle_forecast)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    _register_all_handlers()
    run_worker([QueueName.SIMULATION, QueueName.CONNECTOR_SYNC, QueueName.AI_AGENT])
