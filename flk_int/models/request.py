import time


class Request:
    def __init__(self, request_id, caller_id, prompt_tokens, max_output_tokens, priority):
        self.request_id = request_id
        self.caller_id = caller_id
        self.prompt_tokens = prompt_tokens
        self.max_output_tokens = max_output_tokens
        self.priority = priority
        self.state = "QUEUED"
        self.phase = None
        self.block_table = []
        self.worker_id = None
        self.batch_id = None
        self.submitted_at = time.time()
        self.actual_output_tokens = None
