"""Composition root: FastAPI application wiring.

This module is the only place allowed to depend on every layer (it wires
controllers, use cases, and infrastructure together). It is intentionally
outside the import-linter layer contract.
"""

from fastapi import FastAPI

app = FastAPI(title="Aim Trainer API")


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}
