# Qubit Queue

A simulator-first quantum workload scheduler built with FastAPI, Redis, RQ, and Qiskit Aer.

## Milestone 1: FIFO baseline

Submit a validated circuit, receive a job ID immediately, execute it in a background worker,
and retrieve status and measurement counts. Multiple workers pull from the same FIFO queue.
This is demand-driven work distribution; explicit resource-aware placement comes later.

```text
Client → FastAPI → Redis FIFO queue → RQ worker → Qiskit Aer
                   ↑ job status and results ←───────────┘
```

FastAPI handles HTTP requests. Redis stores queued work and job metadata. RQ manages worker
execution and job states. Qiskit constructs circuits; Aer simulates them on classical CPUs.
The API process does not perform quantum simulation.

## Run with Docker

Install Docker Desktop with Linux containers enabled, then open PowerShell in the repository:

```powershell
docker compose up --build --scale worker=2
```

Open http://localhost:8000/docs for the interactive API. Redis is internal to the Compose
network. Its data directory uses a persistent volume and append-only logging. This improves
restart durability but is not a backup or a guarantee against all data loss.

Submit the example:

```powershell
$payload = Get-Content .\examples\bell.json -Raw
$job = Invoke-RestMethod -Method Post -Uri http://localhost:8000/jobs -ContentType 'application/json' -Body $payload
$job
Invoke-RestMethod -Uri "http://localhost:8000/jobs/$($job.job_id)"
```

Poll the last command until `status` is `finished`. The Bell circuit puts two qubits into
an entangled state: ideal measurements produce only `00` and `11`, roughly equally often.
The counts add up to the requested number of shots; a shot is one repeated circuit execution.

Stop services with `docker compose down`. The Redis volume remains unless explicitly removed.

## Python development

Python 3.11 or newer is required. On Windows:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e '.[dev]'
.\.venv\Scripts\python.exe -m pytest
```

The default `rq worker` uses Unix process forking; use Linux containers for the documented
deployment. Tests use an in-process worker and an in-memory Redis substitute so they can run
on Windows. They execute the real Qiskit simulator, but do not verify a real Redis server,
multiple processes, container startup, or crash recovery.

For an API against an existing Redis server:

```powershell
$env:REDIS_URL = 'redis://localhost:6379/0'
.\.venv\Scripts\python.exe -m uvicorn qubit_queue.api:app --reload
```

Start workers separately using the Docker configuration or a Linux environment.

## API contract

| Endpoint | Behavior |
| --- | --- |
| `GET /health` | Checks Redis connectivity; does not check worker availability |
| `POST /jobs` | Returns HTTP 202 with a job ID and status URL |
| `GET /jobs/{id}` | Returns status, timestamps, result, or a generic execution error |

Jobs accept 1–16 qubits, 1–10,000 shots, and 1–1,000 gates. Supported gates are
`h`, `x`, `y`, `z`, `s`, `t`, and `cx`. Every qubit is measured at the end. The seed
defaults to 42 for repeatable local experiments. Unknown gates and invalid qubit references
return HTTP 422 without enqueueing work. Redis connection failures return HTTP 503.

Successful results and failed-job records are retained for 24 hours. Execution has a
120-second timeout in production RQ workers. Retention expiry means the status endpoint
returns HTTP 404. There is no automatic retry or cancellation endpoint yet. Abrupt worker
loss may leave a job started until RQ maintenance detects it; recovery needs dedicated tests
in a later milestone. This initial API has no authentication or per-user rate limiting and
is bound to localhost in Compose for local development.

## Source map

- `src/qubit_queue/models.py`: request schema and validation.
- `src/qubit_queue/api.py`: API and queue integration.
- `src/qubit_queue/tasks.py`: circuit construction and simulator execution.
- `tests/test_jobs.py`: API-to-worker lifecycle and validation checks.
- `examples/bell.json`: a small known circuit for the first demonstration.
- `docs/ROADMAP.md`: remaining implementation and evaluation plan.

## Technical references

- [Qiskit Aer simulator guide](https://qiskit.github.io/qiskit-aer/tutorials/1_aersimulator.html)
- [RQ documentation](https://python-rq.org/docs/)
- [FastAPI documentation](https://fastapi.tiangolo.com/)

Dependency ranges live in `pyproject.toml`. GitHub Actions runs the tests on Linux.
Local dependency installation during initial setup failed because the C: drive ran out of
space; runtime tests and the container deployment have not yet been verified. Add a tested
dependency lock after the first successful runtime validation.
