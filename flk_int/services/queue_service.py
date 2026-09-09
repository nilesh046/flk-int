from flk_int.factories.request_factory import RequestFactory


class QueueService:
    def __init__(self):
        self.requests = {}
        self.queue = []

    def add(self, request_id, caller_id, prompt_tokens, max_output_tokens, priority, block_table):
        req = RequestFactory.create(request_id, caller_id, prompt_tokens, max_output_tokens, priority)
        req.block_table = block_table
        self.requests[request_id] = req
        self.queue.append(req)
        return req

    def cancel(self, request_id):
        req = self.requests.get(request_id)
        if req is None:
            raise ValueError(f"{request_id} not found")
        if req.state != "QUEUED":
            raise ValueError(f"{request_id} is {req.state}, cannot cancel")
        req.state = "CANCELLED"
        self.queue = [r for r in self.queue if r.request_id != request_id]
        blocks = req.block_table
        req.block_table = []
        return blocks

    def next_batch(self, max_batch_size, priority_strategy):
        runnable = [r for r in self.queue if r.state == "QUEUED"]
        if not runnable:
            return []
        ordered = priority_strategy.sort_queue(runnable)
        return ordered[:max_batch_size]

    def remove_from_queue(self, req):
        self.queue.remove(req)

    def get(self, request_id):
        return self.requests.get(request_id)

    def show(self, request_id):
        req = self.requests.get(request_id)
        if req is None:
            print(f"{request_id}: not found")
            return
        print(f"{request_id}: state={req.state}, phase={req.phase}, worker={req.worker_id}, batch={req.batch_id}, blocks={len(req.block_table)}")
