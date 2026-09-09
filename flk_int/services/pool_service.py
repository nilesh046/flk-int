from flk_int.models.kv_block_pool import KVBlockPool


class PoolService:
    def __init__(self):
        self.pool = None

    def setup(self, num_blocks, block_size):
        self.pool = KVBlockPool(num_blocks, block_size)

    def reserve(self, prompt_tokens, max_output_tokens):
        n = self.pool.blocks_needed(prompt_tokens, max_output_tokens)
        if n > self.pool.free_count():
            raise ValueError("Not enough free blocks")
        return self.pool.allocate(n)

    def release(self, block_table):
        self.pool.release(block_table)

    def show(self):
        print(f"pool: free={self.pool.free_count()}, used={self.pool.used_count()}")
