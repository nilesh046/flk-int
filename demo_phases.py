from flk_int.services.scheduler import InferenceScheduler

s = InferenceScheduler()

# max_batch_size=3 so all three go in one batch
s.onboard_pool(40, 16, 3, 100)
s.onboard_worker("w1")

s.submit("r1", "search", 10, 10, "INTERACTIVE")
s.submit("r2", "ads",    10, 10, "INTERACTIVE")
s.submit("r3", "order",  10, 10, "BATCH")

# all 3 fit, single batch on w1
s.plan_and_run()

s.show_request("r1")   # PREFILL
s.show_request("r2")   # PREFILL
s.show_request("r3")   # PREFILL

# one plan_and_run step moves all to DECODE
s.plan_and_run()

s.show_request("r1")   # DECODE
s.show_request("r2")   # DECODE
s.show_request("r3")   # DECODE

# complete all in one shot
s.complete_batch("w1", "b-1", {"r1": 5, "r2": 3, "r3": 7})

s.show_request("r1")
s.show_request("r2")
s.show_request("r3")
s.show_pool()
