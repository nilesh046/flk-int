from flk_int.services.scheduler import InferenceScheduler

s = InferenceScheduler()

print("--- setup ---")
s.onboard_pool(20, 16, 4, 100)
s.onboard_worker("w1")
s.onboard_worker("w2")
s.show_pool()

print("\n--- submit r1, r2 ---")
s.submit("r1", "search", 40, 50, "INTERACTIVE")
s.submit("r2", "search", 30, 20, "INTERACTIVE")

print("\n--- plan_and_run: r1->w1, r2->w2 (both enter PREFILL) ---")
s.plan_and_run()
s.plan_and_run()
s.show_request("r1")
s.show_request("r2")

print("\n--- submit r3 while both workers busy ---")
s.submit("r3", "ads", 20, 10, "BATCH")
s.show_request("r3")

print("\n--- plan_and_run again: r1,r2 advance to DECODE ---")
s.plan_and_run()
s.show_request("r1")
s.show_request("r2")

print("\n--- cancel r3 (still QUEUED) ---")
s.cancel("r3")

print("\n--- cancel r1 (RUNNING, should reject) ---")
s.cancel("r1")

print("\n--- complete r1 on w1 (actual=20, valid) ---")
s.complete_batch("w1", "b-1", {"r1": 20})
s.show_request("r1")

print("\n--- complete r2 on w2 with bad actual (actual=999, rejected) ---")
s.complete_batch("w2", "b-2", {"r2": 999})
s.show_request("r2")

print("\n--- submit r4 (INTERACTIVE) and r5 (BATCH), priority should pick r4 first ---")
s.submit("r4", "order", 10, 10, "INTERACTIVE")
s.submit("r5", "ads", 10, 10, "BATCH")
s.plan_and_run()
s.show_request("r4")
s.show_request("r5")

print("\n--- complete r4, r5 should auto-schedule ---")
s.complete_batch("w1", "b-3", {"r4": 5})
s.show_request("r4")
s.show_request("r5")

print("\n--- final pool ---")
s.show_pool()
