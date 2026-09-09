from flk_int.services.scheduler import InferenceScheduler

s = InferenceScheduler()

# setup: 20 blocks, each block = 16 tokens, 1 request per batch, 100ms max wait
s.onboard_pool(20, 16, 1, 100)
s.onboard_worker("w1")
s.onboard_worker("w2")

s.show_pool()

# r1: 40 prompt + 50 max_output = 90 tokens -> ceil(90/16) = 6 blocks
s.submit("r1", "search", 40, 50, "INTERACTIVE")

# r2: 30 + 20 = 50 -> ceil(50/16) = 4 blocks
s.submit("r2", "search", 30, 20, "INTERACTIVE")

s.plan_and_run()   # r1 -> w1, PREFILL
s.plan_and_run()   # r2 -> w2, PREFILL

s.show_request("r1")
s.show_request("r2")
s.show_worker("w1")
s.show_worker("w2")
s.show_pool()

# r3: 20 + 10 = 30 -> ceil(30/16) = 2 blocks reserved, but no free worker yet
s.submit("r3", "search", 20, 10, "BATCH")
s.show_request("r3")
s.show_pool()

# complete r1: actual=20 is valid (20 <= 50), w1 frees up
# r3 should auto-schedule onto w1
s.complete_batch("w1", "b-1", {"r1": 20})
s.show_request("r1")
s.show_request("r3")
s.show_pool()

s.complete_batch("w2", "b-2", {"r2": 15})
s.complete_batch("w1", "b-3", {"r3": 5})

s.show_pool()
