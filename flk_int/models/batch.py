class Batch:
    _counter = 0

    def __init__(self, requests, worker_id):
        Batch._counter += 1
        self.batch_id = f"b-{Batch._counter}"
        self.worker_id = worker_id
        self.requests = requests
