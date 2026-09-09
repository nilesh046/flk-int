from flk_int.services.scheduler import InferenceScheduler

s = InferenceScheduler()

s.onboard_pool(20, 16, 1, 100)
s.onboard_worker("w1")

# --- test cancel while QUEUED ---

s.submit("r1", "search", 20, 10, "INTERACTIVE")
s.show_request("r1")

# r1 not yet assigned to any worker, cancel should work
s.cancel("r1")
s.show_request("r1")
s.show_pool()   # blocks should be back

# --- test cancel while RUNNING (rejected) ---

s.submit("r2", "ads", 20, 10, "INTERACTIVE")
s.plan_and_run()
s.show_request("r2")

s.cancel("r2")   # should print: cannot cancel

# --- test bad actual_output in complete_batch ---

# actual=999 is way over max_output=10, batch gets rejected
# note: worker still frees after this, but r2 blocks remain used (leak)
s.complete_batch("w1", "b-1", {"r2": 999})

s.show_request("r2")   # still RUNNING, not finished
s.show_pool()          # used=2, those blocks are stuck

# system still functional - submit and run a new request
s.submit("r3", "order", 10, 5, "INTERACTIVE")
s.plan_and_run()
s.complete_batch("w1", "b-2", {"r3": 3})
s.show_request("r3")
s.show_pool()
