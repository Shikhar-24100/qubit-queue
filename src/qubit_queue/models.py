from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Gate(BaseModel):
    name: Literal["h", "x", "y", "z", "s", "t", "cx"]
    qubits: list[int] = Field(min_length=1, max_length=2)

    @model_validator(mode="after")
    def validate_arity(self):
        expected = 2 if self.name == "cx" else 1
        if len(self.qubits) != expected:
            raise ValueError(f"{self.name} requires {expected} qubit(s)")
        if min(self.qubits) < 0 or len(set(self.qubits)) != len(self.qubits):
            raise ValueError("Qubit indices must be nonnegative and distinct")
        return self


class CircuitJob(BaseModel):
    # Statevector memory grows exponentially; keep the initial lab workload small.
    qubits: int = Field(ge=1, le=16)
    shots: int = Field(default=1024, ge=1, le=10000)
    gates: list[Gate] = Field(min_length=1, max_length=1000)
    seed: int = Field(default=42, ge=0, le=2**32 - 1)

    @model_validator(mode="after")
    def validate_indices(self):
        if any(index >= self.qubits for gate in self.gates for index in gate.qubits):
            raise ValueError("Gate index is outside the circuit's qubit range")
        return self
