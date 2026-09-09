Flipkart Inference Platform – Paged KV-Cache

1. Overall Problem Statement

You need to implement the scheduling and memory-management core for Flipkart's LLM inference platform.

Conceptually, your system sits between:

Incoming inference requests → Scheduler / KV-memory manager → GPU worker pool

The system does not need to run an actual LLM. You are expected to simulate the necessary classes and methods.

Why KV-cache management is required

GPU memory for LLM inference is dominated by the KV cache.

The KV cache consists of per-layer Key/Value tensors for every token that has already been processed.

Instead of managing memory token-by-token, GPU memory is divided into fixed-size blocks.

Example:

block_size = 16 tokens

So if a request needs space for 16 tokens, it needs 1 block.
If it needs 17 tokens, it needs 2 blocks.

Each request/sequence maintains a:

block table = list of physical block IDs allocated to that request

Your system therefore needs to manage:

Physical KV blocks
Per-sequence/request block tables
GPU workers
Incoming requests
Scheduling
Batch execution
Request lifecycle/state
Cancellation
Memory reservation and release
Thread safety
2. Important Memory Requirement

When a request arrives, you know:

prompt_tokens
max_output_tokens

But you do not know the actual output length yet.

Therefore, KV memory must initially be reserved for the worst case:

prompt_tokens + max_output_tokens

The actual output length becomes known only as the model generates tokens step-by-step.

This creates an important requirement:

Some of the blocks reserved initially may never actually be needed.

Those unused blocks must ultimately be freed when the request completes.

Example

Suppose:

prompt = 40 tokens
max_output = 50 tokens
block_size = 16

Worst-case tokens:

40 + 50 = 90

Required blocks:

ceil(90 / 16) = 6 blocks

So 6 blocks must be reserved initially.

If the request actually generates only:

20 output tokens

then actual tokens are:

40 + 20 = 60

which would only require:

ceil(60 / 16) = 4 blocks

The remaining reserved capacity must not leak; all blocks in the request's block table are eventually returned to the pool on completion, according to the specification.

3. Core Requirements

The document divides the assignment into six core areas.

Requirement 1 — Onboarding

The system must support onboarding:

GPU workers
KV block pool configuration
GPU workers

Each GPU worker can run:

one batch at a time

So a worker has essentially two relevant states:

IDLE
RUNNING

An incoming request can only start running if a suitable worker is free.

KV block pool configuration

The pool has four configuration values:

Configuration	Meaning
num_blocks	Total number of physical KV blocks
block_size	Number of tokens represented by one block, e.g. 16
max_batch_size	Maximum number of requests that can be in a batch
max_wait_ms	Maximum time a queued request can wait before it must be scheduled

The document says to assume num_blocks is shared across all workers unless you explicitly document another design.

This is important:

Total physical blocks = global pool

rather than automatically assuming:

blocks per GPU worker
4. Request Submission & Cancellation

Requests contain:

request_id
prompt_tokens
max_output_tokens
priority

The sample command also explicitly includes caller_id.

So the practical request structure is:

request_id
caller_id
prompt_tokens
max_output_tokens
priority
Priority values

There are two priorities:

INTERACTIVE
BATCH

Meaning:

INTERACTIVE → immediate processing
BATCH → batch processing

The bonus section later further specifies how these priorities should interact.

Cancellation

Cancellation is deliberately restricted.

A request can be cancelled only while it is QUEUED.

A queued request may be waiting because:

no GPU worker is free
there aren't enough KV blocks
If cancellation succeeds

The system must:

Mark the request as cancelled.
Ensure it never runs.
Free all reserved blocks belonging to it.
If request is already running

If:

state = RUNNING

meaning its batch has already started on a worker:

cancel → REJECT

You cannot cancel it through this API.

This distinction is important for race conditions as well:

QUEUED → cancellation allowed

RUNNING → cancellation rejected
5. KV Block Reservation & Settlement

This is one of the central parts of the problem.

On submission

Reserve the worst-case amount of memory.

Formula:

required_tokens =
    prompt_tokens + max_output_tokens

Then:

required_blocks =
    ceil(required_tokens / block_size)

Those physical blocks are reserved and recorded in the request's block table.

On completion

When a batch finishes, the caller supplies:

actual_output_tokens

The system must validate it.

Invalid completion

If:

actual_output_tokens > max_output_tokens

then:

REJECT COMPLETION

The system must not trust the caller.

This is essentially an input-validation / invariant requirement.

Valid completion

If the actual output count is valid:

actual_output_tokens <= max_output_tokens

then:

free all blocks in the request's block table

and return them to the pool.

Critical memory guarantees

The implementation must guarantee:

No leaked blocks
No double-freed blocks

This means your block allocator/releaser needs to be carefully designed.

6. Scheduling & Batch Execution

Two important operations are explicitly required:

plan_and_run()
complete_batch()
plan_and_run()

Its responsibility is to:

Select queued requests.
Form a batch.
Find a free worker.
Assign the batch to that worker.
Start/advance execution.
complete_batch()

Called when a worker finishes executing its batch.

It is responsible for completing the requests and returning their KV blocks.

7. Request Execution Phases

Each request has two conceptual execution phases.

Phase	When	What happens
Prefill	First step	Process the full prompt
Decode	After prefill	Generate one token per batch step until done

So conceptually:

Request
   |
   v
PREFILL
   |
   v
DECODE
   |
   | one token per batch step
   v
DONE

This is important because the assignment is modelling LLM inference execution, even though you're not actually running an LLM.

8. Scheduling Rules

There are several hard constraints.

Rule 1 — Batch size

A batch can contain at most:

max_batch_size

requests.

So if:

max_batch_size = 4

then:

batch size <= 4
Rule 2 — Global memory limit

At no point can:

total blocks in use > num_blocks

This is a hard invariant.

For example:

num_blocks = 20

used = 18
new request needs 3 blocks

It cannot be scheduled because:

18 + 3 = 21 > 20

The request must remain queued.

Rule 3 — No free worker

If there is no free worker:

request → QUEUED

It must wait.

Rule 4 — Not enough KV blocks

If there aren't enough free physical blocks:

request → QUEUED

Again, it waits rather than partially allocating or overcommitting memory.

Rule 5 — Retry scheduling

The scheduler should try scheduling again when either:

(a) a worker becomes free

or:

(b) blocks are returned after completion

This is important because either event can unblock a queued request.

9. Continuous Batching

The assignment explicitly asks for continuous batching.

The key rule is:

When a request completes, remove it from the current batch; a queued request can join the next batch.

Conceptually:

Batch:
[R1, R2, R3, R4]

R2 completes

Next batch:
[R1, R3, R4, R5]
             ^
             |
       queued request

You therefore shouldn't think of the batch as permanently fixed for the entire lifetime of the system.

Requests can flow in as other requests complete.

10. Status Tracking

The system must provide ways to inspect its internal state during a demo.

The document gives example APIs:

show_request()
show_worker()
show_pool()

The exact field names and output format are left to you.

You can use:

strings
JSON
objects
etc.
show_pool()

Must allow you to determine:

free blocks
used blocks

Example:

free=14, used=6
show_worker()

Must show whether the worker is:

IDLE

or:

RUNNING

and ideally what it's running.

show_request()

Must tell you whether a request is:

WAITING / QUEUED
RUNNING
FINISHED

The underlying implementation can have additional states, such as CANCELLED, if useful.

11. Concurrency & Thread Safety

The following operations must be thread-safe:

submit
cancel
plan_and_run
complete_batch

This means the system must correctly handle concurrent calls without corrupting:

request state
worker state
block allocation
block release
queues
batch assignments
12. Bonus Features

These should only be attempted after P0/core requirements are complete.

There are two bonus areas.

Bonus 1 — Fair Queueing

Instead of strict FCFS:

First Come → First Served

implement fair queueing using round-robin across callers.

The document suggests callers such as:

search
ads
order

For example, instead of:

search
search
search
search
ads
order

you could conceptually rotate:

search
ads
order
search
ads
order
...

The bonus also says to:

add limits

The exact limits are left for you to design.

13. Bonus 2 — Priority

Priority should be:

INTERACTIVE > BATCH

So interactive requests should generally be scheduled before batch requests.

However:

BATCH must not starve forever.

So you need some mechanism that ensures a continuously arriving stream of interactive requests cannot permanently prevent batch requests from running.

This is essentially a fairness/starvation problem.

14. Guidelines / Constraints

The assignment gives the following implementation constraints.

Time
90 minutes

So the expectation is not to build a production-scale distributed inference platform.

Code

Code should be:

modular
demo-able

and should have either:

main

or:

tests

to demonstrate functionality.

Storage

The system must be:

IN-MEMORY ONLY

Do not use:

HTTP
Database
AI tools
Language

Any of these are acceptable:

Java
C++
Rust
Go
Python
Assumptions

You should explicitly state your assumptions.

This is important because the prompt intentionally leaves some implementation choices open.

15. Evaluation Criteria

The evaluator will look at:

Correctness
Entity modeling
Modularity
Thread safety
Edge cases
Readable code

So this isn't simply an algorithm question.

They are also evaluating whether you model the domain properly.

16. Sample Test / Command Interface

The document provides an illustrative command interface.

Command	Parameters / Behavior
onboard_pool	num_blocks, block_size, max_batch_size, max_wait_ms
onboard_worker	worker_id
submit_request	request_id, caller_id, prompt_tokens, max_output_tokens, priority
cancel_request	request_id
plan_and_run	picks batch, assigns free worker, advances clock
complete_batch	worker_id, batch_id, {request_id: actual_output_tokens}
show_request	request_id
show_worker	worker_id
show_pool	no parameter

The document specifically says the format is illustrative, so you don't have to literally build a CLI with this syntax.

17. Full Example From Pages 5–6

The last two pages give a concrete execution example.

Step 1 — Create the KV pool

Input:

onboard_pool(20, 16, 4, 100)

Meaning:

num_blocks    = 20
block_size    = 16 tokens
max_batch_size = 4
max_wait_ms   = 100

Output:

pool ready

Then:

show_pool()

returns:

free=20, used=0

So initially:

20 free
0 used
18. Add Worker w1

Input:

onboard_worker("w1")

Output:

worker w1 ready

Worker w1 is now available.

19. Add Worker w2

Input:

onboard_worker("w2")

Output:

worker w2 ready

Now there are two GPU workers:

w1 → ready/free
w2 → ready/free
20. Submit Request r1

Input:

submit_request(
    "r1",
    "search",
    40,
    50,
    INTERACTIVE
)

The parameters are:

request_id       = r1
caller_id        = search
prompt_tokens    = 40
max_output_tokens = 50
priority         = INTERACTIVE

Worst-case token requirement:

40 + 50 = 90 tokens

With:

block_size = 16

required blocks:

ceil(90 / 16) = 6

The example therefore shows:

accepted, assigned to w1

and:

pool: free=14, used=6

So:

20 total
- 6 allocated to r1
= 14 free

The example associates r1 with worker w1.

21. Submit Request r2

Input:

submit_request(
    "r2",
    "search",
    30,
    20,
    INTERACTIVE
)

Parameters:

request_id        = r2
caller_id         = search
prompt_tokens     = 30
max_output_tokens = 20
priority          = INTERACTIVE

Worst-case tokens:

30 + 20 = 50

Required blocks:

ceil(50 / 16) = 4

So the pool becomes:

20 total
- 6 for r1
- 4 for r2
= 10 free

The example shows:

accepted, assigned to w2

followed by:

pool: free=10, used=10

So the state is:

w1 → r1
w2 → r2

KV:
10 free
10 used
22. Submit Request r3

Input:

submit_request(
    "r3",
    "search",
    20,
    10,
    BATCH
)

Worst-case tokens:

20 + 10 = 30

Required blocks:

ceil(30 / 16) = 2

The example shows:

accepted, waiting

and:

pool: free=8, used=12

So r3 has had its 2 blocks reserved:

r1 → 6 blocks
r2 → 4 blocks
r3 → 2 blocks

Total used = 12
Free = 8

But r3 is waiting, rather than running.

This demonstrates an important distinction:

Having enough KV blocks does not by itself mean a request can run. A free worker is also required.

At this point both workers are occupied:

w1 → r1
w2 → r2

Therefore:

r3 → QUEUED
23. Complete r1

Input:

complete_batch(
    "w1",
    "b-1",
    {"r1": 20}
)

Meaning:

worker_id = w1
batch_id  = b-1
r1 actual output = 20 tokens

Since:

actual_output_tokens = 20
max_output_tokens    = 50

this is valid:

20 <= 50

The example reports:

r1 finished

and:

pool: free=14, used=6

This means the request's six reserved blocks have been returned.

Before completion:

free = 8
used = 12

After freeing r1's 6 blocks:

free = 14
used = 6
24. Show r1

Input:

show_request("r1")

Output:

(finished)

So the request lifecycle demonstrated is essentially:

r1
 ↓
accepted
 ↓
assigned to w1
 ↓
running
 ↓
complete_batch
 ↓
finished
 ↓
blocks returned
25. Complete Assignment in One Picture

The overall system you need to build can be understood as:

                         ┌─────────────────────┐
                         │   Incoming Request  │
                         │                     │
                         │ request_id          │
                         │ caller_id           │
                         │ prompt_tokens       │
                         │ max_output_tokens   │
                         │ priority            │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       SUBMIT        │
                         └──────────┬──────────┘
                                    │
                         Reserve worst-case KV
                         blocks immediately
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       QUEUED        │
                         └──────────┬──────────┘
                                    │
                         ┌──────────┴──────────┐
                         │                     │
                  Free worker?           Enough blocks?
                         │                     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   PLAN_AND_RUN      │
                         │                     │
                         │ form batch          │
                         │ assign worker       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      RUNNING        │
                         └──────────┬──────────┘
                                    │
                             ┌──────┴──────┐
                             │             │
                          Prefill        Decode
                             │             │
                             │      one token/batch
                             │         step
                             └──────┬──────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │  COMPLETE_BATCH     │
                         └──────────┬──────────┘
                                    │
                         validate actual output
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      FINISHED       │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         Free all KV blocks
                                    │
                                    ▼
                         Try scheduling queued
                              requests again
26. Entities You Are Essentially Expected to Model

The prompt doesn't dictate class names, but based strictly on its requirements, the natural domain entities are:

Request

Should contain things such as:

request_id
caller_id
prompt_tokens
max_output_tokens
priority
state
block_table
worker_id
batch_id
submission_time / enqueue_time
actual_output_tokens
KVBlockPool

Responsible for:

num_blocks
block_size

allocate blocks
release blocks
track free blocks
track used blocks

Invariant:

0 <= used_blocks <= num_blocks
Worker

Responsible for:

worker_id
state
current_batch

With the fundamental constraint:

one batch per worker
Batch

Would naturally contain:

batch_id
worker_id
requests

and potentially execution state.

Scheduler

Responsible for:

submit
cancel
plan_and_run
complete_batch
queue management
priority
worker selection
batch formation
Request State

At minimum, the specification requires you to distinguish:

QUEUED
RUNNING
FINISHED

and cancellation naturally introduces:

CANCELLED

You may also define other internal states if useful.

27. Most Important Invariants

If you were preparing for an interview/implementation, these are the rules I would treat as non-negotiable invariants from the document.

Memory
used_blocks <= num_blocks

Never over-allocate.

Allocation

For every accepted request:

allocated_blocks =
ceil(
    (prompt_tokens + max_output_tokens)
    / block_size
)
Release

When a valid request completes:

all blocks in its block table → pool
Double free

Never release the same block twice.

Leak

Every allocated block must eventually be released on:

completion
or
queued cancellation
Completion validation
actual_output_tokens <= max_output_tokens

Otherwise reject completion.

Worker
one worker = at most one active batch
Batch
batch_size <= max_batch_size
Scheduling

A request can run only if:

worker is free
AND
enough KV blocks are available
Cancellation
QUEUED → cancellation allowed
RUNNING → cancellation rejected
Cancelled request
CANCELLED → must never run
Rescheduling

Try scheduling when:

worker becomes free
OR
KV blocks are returned
Thread safety

These operations must be safe under concurrent invocation:

submit()
cancel()
plan_and_run()
complete_batch()
28. What Is Core vs Bonus
P0 / Core — MUST DO

From the document:

✓ GPU worker onboarding
✓ KV pool onboarding
✓ Physical block management
✓ Request submission
✓ Worst-case KV reservation
✓ Per-request block table
✓ Queueing
✓ Worker assignment
✓ Batch formation
✓ max_batch_size
✓ Prefill / Decode modelling
✓ Completion
✓ Actual-output validation
✓ Block release
✓ Cancellation
✓ Worker status
✓ Request status
✓ Pool status
✓ Continuous batching
✓ Thread safety
✓ Edge cases
Bonus — ONLY AFTER P0
○ Fair queueing across callers
○ Round-robin scheduling
○ Caller limits
○ INTERACTIVE priority
○ Prevent BATCH starvation
29. What the Interviewer Is Really Testing

The assignment is not asking you to implement an LLM.

It is primarily testing whether you can design a concurrent in-memory resource scheduler around an LLM-serving workload.

The major design problems are:

              ┌──────────────────┐
              │ Request Lifecycle│
              └────────┬─────────┘
                       │
        ┌──────────────┼───────────────┐
        ▼              ▼               ▼
   KV Allocation   Scheduling      Cancellation
        │              │               │
        └──────────────┼───────────────┘
                       ▼
                Worker Management
                       │
                       ▼
                 Batch Execution
                       │
                       ▼
                Resource Release

The hardest parts are likely to be:

Correct KV block accounting
Correct request state transitions
Worker/batch assignment
Cancellation races
Completion races
Avoiding double allocation/free
Thread-safe scheduling
Correct queue behavior
Continuous batching
Handling insufficient workers vs insufficient memory independently
One subtle but important observation about the supplied example

The sample is explicitly labelled “Format is illustrative.”

So you should treat the example as demonstrating the intended concepts and accounting rather than assuming every internal transition shown there is a mandatory API behavior.

For example, the sample shows submit_request(r1) immediately as “accepted, assigned to w1”, whereas the core requirements separately define plan_and_run() as the operation that forms a batch and assigns a free worker.

For an implementation, I would therefore preserve the core requirement that scheduling is performed by plan_and_run(), while treating the sample's immediate assignment output as illustrative.

Final condensed problem statement

Build an in-memory, thread-safe LLM inference scheduler that manages a shared pool of fixed-size KV-cache blocks and a pool of GPU workers.

When a request arrives, calculate and reserve KV blocks for:

prompt_tokens + max_output_tokens

Store those physical block IDs in the request's block table.

Keep requests queued until both:

a GPU worker is free
AND
enough KV blocks are available

Use plan_and_run() to form batches of at most max_batch_size requests and assign them to free workers.

Model:

Prefill → Decode → Complete

where decode generates one token per batch step.

Allow cancellation only while queued. A cancelled request must never execute and must release all reserved blocks. Running requests cannot be cancelled.

When a batch completes, validate the caller-provided actual output length, reject it if it exceeds the declared maximum, otherwise mark requests finished and return their blocks to the pool without leaks or double frees.

Whenever a worker becomes free or blocks are returned, queued requests should become eligible for scheduling again.

Expose request, worker, and pool status for demonstration.

Make submit, cancel, plan_and_run, and complete_batch thread-safe.

After all of that works, optionally implement fair round-robin queueing across callers and priority handling where INTERACTIVE gets preference without permanently starving BATCH.

That is the complete problem contained in the 6-page PDF, including the requirements, constraints, bonus features, commands, examples, and the information shown in the page images.