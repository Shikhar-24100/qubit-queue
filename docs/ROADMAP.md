# Implementation and evaluation plan

We implement one working milestone at a time and commit each verified change.

## 1. FIFO baseline

Build submission, validation, a shared Redis queue, simulator workers, and result retrieval.
Use a Bell circuit to verify correctness. Run two container workers against real Redis before
claiming the distributed deployment is verified.

## 2. Scheduling policies

Add an explicit scheduling layer ahead of the execution queue. Compare FIFO, priority with
aging, and estimated-shortest-job-first. Keep dispatch bounded by available execution slots:
if every job is immediately transferred to an execution FIFO, later scheduling choices
cannot reorder waiting work. Define stable tie-breaking, concurrency-safe selection, and
the behavior of policy changes while jobs are queued.

Store arrival, dispatch, start, and finish timestamps. Define waiting time consistently as
submission-to-execution-start. Begin with a documented cost heuristic based on qubits,
gate count/depth, and shots. It is an estimate, not an accurate physical runtime model.

## 3. Reliability and worker coordination

Add worker visibility, bounded retries, duplicate-submission protection, queued-job
cancellation, and failure recovery. Test worker termination, Redis interruption, timeouts,
and restarts against real services. Make job state transitions and retry history inspectable.
Resource-aware scheduling can follow once worker capacity and simulator memory estimates
are available. Avoid claiming exactly-once execution without a demonstrated protocol.

## 4. Benchmark

Generate seeded workloads with a mix of circuit sizes and depths. Use identical workloads,
worker counts, simulator settings, and arrival patterns for every policy. Repeat experiments
and report mean and percentile waiting time, turnaround time, throughput, failure rate,
and waiting time by priority class. Priority policies trade fairness across classes; do not
judge them on average waiting time alone. Include both a queued burst and staggered arrivals.

Separate queue overhead from actual simulation time. Record CPU/memory, environment,
dependency versions, and raw observations. Produce reproducible tables and plots rather
than claiming a policy always wins.

## 5. Presentation

Add a small dashboard showing queue depth, worker activity, job progress, and benchmark
comparisons. Prepare architecture, scheduling pseudocode, test evidence, limitations,
and a repeatable demonstration. Cloud quantum hardware is an optional extension after
the local system is reliable; provider queues remain outside our control.
