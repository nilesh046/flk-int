from flk_int.services.scheduler import InferenceScheduler

s = InferenceScheduler()

s.onboard_pool(20, 16, 1, 100)
s.onboard_worker("w1")

# submit BATCH first, then INTERACTIVE after
# InteractiveFirstStrategy should pick r2 (INTERACTIVE) over r1 (BATCH)
s.submit("r1", "ads", 10, 10, "BATCH")
s.submit("r2", "search", 10, 10, "INTERACTIVE")

print("\n-- queue: r1=BATCH, r2=INTERACTIVE -- expect r2 to go first --")
s.plan_and_run()

s.show_request("r1")   # QUEUED, skipped
s.show_request("r2")   # RUNNING, PREFILL

# step: r2 advances to DECODE
s.plan_and_run()
s.show_request("r2")

# complete r2, r1 should auto-schedule onto w1
s.complete_batch("w1", "b-1", {"r2": 5})

s.show_request("r2")   # FINISHED
s.show_request("r1")   # now RUNNING
s.show_pool()

s.complete_batch("w1", "b-2", {"r1": 8})
s.show_request("r1")
s.show_pool()
