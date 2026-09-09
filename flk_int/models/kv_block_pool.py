import math


class KVBlockPool:
    def __init__(self, num_blocks, block_size):
        self.num_blocks = num_blocks
        self.block_size = block_size
        self.free_blocks = list(range(num_blocks))
        self.used_blocks = set()

    def blocks_needed(self, prompt_tokens, max_output_tokens):
        # worst case: prompt + max output
        total = prompt_tokens + max_output_tokens
        return math.ceil(total / self.block_size)

    def allocate(self, n):
        if len(self.free_blocks) < n:
            raise ValueError("Not enough free blocks")

        allocated = self.free_blocks[:n]
        self.free_blocks = self.free_blocks[n:]

        for b in allocated:
            self.used_blocks.add(b)

        return allocated

    def release(self, block_table):
        for b in block_table:
            if b not in self.used_blocks:
                # should never happen if cancel/complete are correct
                raise ValueError(f"Block {b} is not in use — possible double free")
            self.used_blocks.remove(b)
            self.free_blocks.append(b)

    def free_count(self):
        return len(self.free_blocks)

    def used_count(self):
        return len(self.used_blocks)
