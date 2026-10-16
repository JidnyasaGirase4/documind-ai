"""Background worker for document processing.

    python -m app.worker          # a dedicated worker process (set WORKER_EMBEDDED=false for the API)

By default the API also runs one worker thread (WORKER_EMBEDDED=true) so a single `uvicorn` command is enough in
development. Several workers can run at once: jobs are claimed atomically in MySQL, so none is processed twice."""

import logging
import os
import socket
import threading
import time
import uuid

from app.core.config import settings
from app.services import job_service

logger = logging.getLogger("documind.worker")
_RECOVER_EVERY_SECONDS = 30.0


def new_worker_id() -> str:
    return f"{socket.gethostname()}-{os.getpid()}-{uuid.uuid4().hex[:6]}"


def process_one(worker_id: str) -> bool:
    """Claims and runs a single due job. Returns False when the queue had nothing runnable."""
    job_id = job_service.claim_next(worker_id)
    if job_id is None:
        return False
    logger.info("Worker %s picked up job %s", worker_id, job_id)
    job_service.run_job(job_id, worker_id)
    return True


def drain(worker_id: str = "drain", limit: int = 1000) -> int:
    """Runs every currently due job, then returns how many ran. Used by tests and one-off scripts."""
    count = 0
    while count < limit and process_one(worker_id):
        count += 1
    return count


def run_forever(stop: threading.Event, worker_id: str | None = None) -> None:
    worker_id = worker_id or new_worker_id()
    last_recover = 0.0
    logger.info("Worker %s started (poll every %.1fs)", worker_id, settings.worker_poll_seconds)
    while not stop.is_set():
        try:
            if time.monotonic() - last_recover >= _RECOVER_EVERY_SECONDS:
                last_recover = time.monotonic()
                job_service.recover_stale()
            if process_one(worker_id):
                continue  # more work may be waiting; do not sleep
        except Exception:
            logger.exception("Worker loop error; continuing")
        stop.wait(settings.worker_poll_seconds)
    logger.info("Worker %s stopped", worker_id)


def start_embedded() -> tuple[threading.Thread, threading.Event]:
    stop = threading.Event()
    thread = threading.Thread(target=run_forever, args=(stop,), daemon=True, name="documind-worker")
    thread.start()
    return thread, stop


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    stop = threading.Event()
    try:
        run_forever(stop)
    except KeyboardInterrupt:
        stop.set()


if __name__ == "__main__":
    main()
