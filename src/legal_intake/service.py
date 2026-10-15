from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .matter_intake import IntakeResult, MatterIngestor, MatterIntake

app = FastAPI(title="Legal matter vector intake")


@app.post("/matters/intake", response_model=IntakeResult)
def receive_signed_matter(intake: MatterIntake) -> IntakeResult:
    client = InfraiClient()
    ingestor = MatterIngestor(
        client=client,
        collection=os.getenv("INFRAI_COLLECTION", "legal-matters"),
        embedding_model=os.getenv("INFRAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )
    try:
        return ingestor.ingest(intake)
    except InfraiError as exc:
        status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(status_code=status, detail={"code": exc.code, "error": exc.detail}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        client.close()
