class Worker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.state = "IDLE"
        self.current_batch = None

    def is_free(self):
        return self.state == "IDLE"

    def assign(self, batch):
        self.state = "RUNNING"
        self.current_batch = batch

    def free(self):
        self.state = "IDLE"
        self.current_batch = None
