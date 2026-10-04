from time import perf_counter

from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator

from qubit_queue.models import CircuitJob


def execute_circuit(payload: dict) -> dict:
    """Executed by an RQ worker, never inside the HTTP request."""
    request = CircuitJob.model_validate(payload)
    started = perf_counter()
    circuit = QuantumCircuit(request.qubits)
    for gate in request.gates:
        getattr(circuit, gate.name)(*gate.qubits)
    depth = circuit.depth()
    circuit.measure_all()
    # Each worker uses one simulator thread to avoid CPU oversubscription.
    simulator = AerSimulator(method="statevector", max_parallel_threads=1)
    compiled = transpile(circuit, simulator, seed_transpiler=request.seed)
    counts = simulator.run(
        compiled, shots=request.shots, seed_simulator=request.seed
    ).result().get_counts()
    return {
        "counts": counts,
        "shots": request.shots,
        "qubits": request.qubits,
        "depth": depth,
        "execution_seconds": perf_counter() - started,
    }
