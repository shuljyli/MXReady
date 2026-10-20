"""Bounded consumers of the durable SQLite scan queue."""

import logging
from threading import Event, Thread

from mxready.services.scans import ScanService

logger = logging.getLogger(__name__)


class ScanWorker:
    def __init__(self, service: ScanService) -> None:
        self.service = service
        self.stopped = Event()
        self.threads: list[Thread] = []

    def start(self) -> None:
        for index in range(self.service.settings.scan_worker_threads):
            thread = Thread(target=self._consume, name=f"scan-worker-{index}", daemon=True)
            self.threads.append(thread)
            thread.start()

    def stop(self) -> None:
        self.stopped.set()
        for thread in self.threads:
            thread.join()

    def _consume(self) -> None:
        while not self.stopped.is_set():
            try:
                self.service.store.recover_expired_jobs()
                for scan_id in self.service.store.queued_job_ids():
                    if self.stopped.is_set():
                        break
                    self.service.run_scan(scan_id)
            except Exception:
                logger.exception("scan queue consumer failed")
            self.stopped.wait(0.5)
