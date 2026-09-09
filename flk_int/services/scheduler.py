from threading import RLock

from flk_int.models.batch import Batch
from flk_int.services.pool_service import PoolService
from flk_int.services.queue_service import QueueService
from flk_int.services.worker_service import WorkerService
from flk_int.strategies.priority_strategy import InteractiveFirstStrategy


class InferenceScheduler:
    def __init__(self):
        self.pool_svc = PoolService()
        self.worker_svc = WorkerService()
        self.queue_svc = QueueService()
        self.max_batch_size = 1
        self._lock = RLock()
        self._priority = InteractiveFirstStrategy()

    def onboard_pool(self, num_blocks, block_size, max_batch_size, max_wait_ms):
        with self._lock:
            self.pool_svc.setup(num_blocks, block_size)
            self.max_batch_size = max_batch_size
            print("pool ready")

    def onboard_worker(self, worker_id):
        with self._lock:
            self.worker_svc.add(worker_id)
            print(f"worker {worker_id} ready")

    def submit(self, request_id, caller_id, prompt_tokens, max_output_tokens, priority):
        with self._lock:
            try:
                blocks = self.pool_svc.reserve(prompt_tokens, max_output_tokens)
            except ValueError as e:
                print(f"{request_id} rejected: {e}")
                return

            self.queue_svc.add(request_id, caller_id, prompt_tokens, max_output_tokens, priority, blocks)
            print(f"{request_id} accepted, queued")
            self.pool_svc.show()

    def cancel(self, request_id):
        with self._lock:
            try:
                block_table = self.queue_svc.cancel(request_id)
            except ValueError as e:
                print(e)
                return

            self.pool_svc.release(block_table)
            print(f"{request_id} cancelled")
            self.pool_svc.show()

    def plan_and_run(self):
        with self._lock:
            # advance any PREFILL requests to DECODE before scheduling next batch
            for w in self.worker_svc.workers.values():
                if w.current_batch:
                    for req in w.current_batch.requests:
                        if req.state == "RUNNING" and req.phase == "PREFILL":
                            req.phase = "DECODE"
                            print(f"{req.request_id} -> DECODE")

            self._schedule()

    def complete_batch(self, worker_id, batch_id, output_map):
        with self._lock:
            worker = self.worker_svc.get(worker_id)
            if worker is None or worker.current_batch is None:
                print(f"nothing active on {worker_id}")
                return

            if worker.current_batch.batch_id != batch_id:
                print(f"batch {batch_id} not active on {worker_id}")
                return

            for req in worker.current_batch.requests:
                actual = output_map.get(req.request_id)

                if actual is None:
                    print(f"{req.request_id}: no output, skipping")
                    continue

                if actual > req.max_output_tokens:
                    print(f"{req.request_id}: rejected — actual {actual} > max {req.max_output_tokens}")
                    continue

                req.actual_output_tokens = actual
                req.phase = "DONE"
                req.state = "FINISHED"
                self.pool_svc.release(req.block_table)
                req.block_table = []
                print(f"{req.request_id} finished")

            worker.free()
            self.pool_svc.show()
            self._schedule()

    def _schedule(self):
        worker = self.worker_svc.get_free()
        if worker is None:
            print("no free worker")
            return

        queued = self.queue_svc.next_batch(self.max_batch_size, self._priority)
        if not queued:
            print("nothing to schedule")
            return

        batch = Batch(queued, worker.worker_id)
        worker.assign(batch)

        for req in queued:
            req.state = "RUNNING"
            req.phase = "PREFILL"
            req.worker_id = worker.worker_id
            req.batch_id = batch.batch_id
            self.queue_svc.remove_from_queue(req)

        print(f"batch {batch.batch_id} on {worker.worker_id}: {[r.request_id for r in queued]}")

    def show_request(self, request_id):
        self.queue_svc.show(request_id)

    def show_worker(self, worker_id):
        self.worker_svc.show(worker_id)

    def show_pool(self):
        self.pool_svc.show()
