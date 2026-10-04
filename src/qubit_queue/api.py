import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from qubit_queue.models import CircuitJob


def create_app(connection=None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app):
        app.state.redis = connection if connection is not None else Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            socket_connect_timeout=2, socket_timeout=5,
        )
        app.state.queue = Queue("circuits", connection=app.state.redis)
        yield
        if connection is None:
            app.state.redis.close()

    app = FastAPI(title="Qubit Queue", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    def health(request: Request):
        try:
            request.app.state.redis.ping()
        except RedisError:
            raise HTTPException(503, "Redis is unavailable")
        return {"status": "ok", "policy": "fifo"}

    @app.post("/jobs", status_code=202)
    def submit(payload: CircuitJob, request: Request):
        try:
            job = request.app.state.queue.enqueue(
                "qubit_queue.tasks.execute_circuit", payload.model_dump(),
                job_timeout=120, result_ttl=86400, failure_ttl=86400,
            )
        except RedisError:
            raise HTTPException(503, "Redis is unavailable")
        return {"job_id": job.id, "status": "queued", "status_url": f"/jobs/{job.id}"}

    @app.get("/jobs/{job_id}")
    def get_job(job_id: str, request: Request):
        try:
            job = Job.fetch(job_id, connection=request.app.state.redis)
            status = job.get_status(refresh=True)
            # Only jobs from our queue and task belong to this API.
            if job.origin != "circuits" or job.func_name != "qubit_queue.tasks.execute_circuit":
                raise HTTPException(404, "Job not found")
            return {
                "job_id": job.id, "status": status,
                "created_at": job.created_at, "started_at": job.started_at,
                "ended_at": job.ended_at,
                "result": job.return_value() if status == "finished" else None,
                "error": "Circuit execution failed; inspect worker logs" if status == "failed" else None,
            }
        except NoSuchJobError:
            raise HTTPException(404, "Job not found or retention period expired")
        except RedisError:
            raise HTTPException(503, "Redis is unavailable")

    return app


app = create_app()
