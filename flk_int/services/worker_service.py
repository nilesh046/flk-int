from flk_int.models.worker import Worker


class WorkerService:
    def __init__(self):
        self.workers = {}

    def add(self, worker_id):
        self.workers[worker_id] = Worker(worker_id)

    def get_free(self):
        for w in self.workers.values():
            if w.is_free():
                return w
        return None

    def get(self, worker_id):
        return self.workers.get(worker_id)

    def show(self, worker_id):
        w = self.workers.get(worker_id)
        if w is None:
            print(f"{worker_id}: not found")
            return
        batch = w.current_batch.batch_id if w.current_batch else "none"
        print(f"{worker_id}: state={w.state}, batch={batch}")
