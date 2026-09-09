from flk_int.models.request import Request


class RequestFactory:
    @staticmethod
    def create(request_id, caller_id, prompt_tokens, max_output_tokens, priority):
        if priority not in ("INTERACTIVE", "BATCH"):
            raise ValueError(f"Unknown priority: {priority}")
        return Request(request_id, caller_id, prompt_tokens, max_output_tokens, priority)
