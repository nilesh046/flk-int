class PriorityStrategy:
    def sort_queue(self, queue):
        raise NotImplementedError


class InteractiveFirstStrategy(PriorityStrategy):
    def sort_queue(self, queue):
        return sorted(queue, key=lambda r: (0 if r.priority == "INTERACTIVE" else 1, r.submitted_at))


class FifoStrategy(PriorityStrategy):
    def sort_queue(self, queue):
        return sorted(queue, key=lambda r: r.submitted_at)
