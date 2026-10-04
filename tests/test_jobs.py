import fakeredis
import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError
from rq import Queue, SimpleWorker
from rq.timeouts import TimerDeathPenalty

from qubit_queue.api import create_app


BELL = {"qubits": 2, "shots": 128, "gates": [
    {"name": "h", "qubits": [0]}, {"name": "cx", "qubits": [0, 1]},
]}


class PortableTestWorker(SimpleWorker):
    death_penalty_class = TimerDeathPenalty


def test_submit_execute_and_retrieve():
    redis = fakeredis.FakeRedis()
    with TestClient(create_app(redis)) as client:
        response = client.post("/jobs", json=BELL)
        assert response.status_code == 202
        url = response.json()["status_url"]
        assert client.get(url).json()["status"] == "queued"
        # SimpleWorker avoids process forking for this in-memory integration test.
        PortableTestWorker([Queue("circuits", connection=redis)], connection=redis).work(burst=True)
        result = client.get(url).json()
        assert result["status"] == "finished"
        assert set(result["result"]["counts"]) == {"00", "11"}
        assert sum(result["result"]["counts"].values()) == 128
        assert result["started_at"] and result["ended_at"]


@pytest.mark.parametrize("change", [
    {"qubits": 17}, {"shots": 0},
    {"gates": [{"name": "cx", "qubits": [0]}]},
    {"gates": [{"name": "cx", "qubits": [0, 0]}]},
    {"gates": [{"name": "h", "qubits": [2]}]},
    {"gates": [{"name": "exec", "qubits": [0]}]},
])
def test_invalid_jobs_never_enter_queue(change):
    redis = fakeredis.FakeRedis()
    with TestClient(create_app(redis)) as client:
        assert client.post("/jobs", json=BELL | change).status_code == 422
        assert Queue("circuits", connection=redis).count == 0


def test_missing_job():
    with TestClient(create_app(fakeredis.FakeRedis())) as client:
        assert client.get("/jobs/missing").status_code == 404


def test_redis_unavailable():
    redis = fakeredis.FakeRedis()
    with TestClient(create_app(redis)) as client:
        redis.ping = lambda: (_ for _ in ()).throw(ConnectionError())
        assert client.get("/health").status_code == 503
