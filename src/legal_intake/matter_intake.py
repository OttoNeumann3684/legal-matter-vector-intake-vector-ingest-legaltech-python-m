from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field

from .infrai_client import InfraiClient


class MatterIntake(BaseModel):
    matter_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    signed_pdf_base64: str = Field(min_length=1)
    signed_at: datetime
    response_deadline: date


class IntakeResult(BaseModel):
    matter_id: str
    delivery_status: str
    indexed_chunks: int
    follow_up_required: bool
    follow_up_on: date


def chunk_text(text: str, size: int = 900, overlap: int = 120) -> list[str]:
    clean = " ".join(text.split())
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        chunks.append(clean[start : start + size])
        if start + size >= len(clean):
            break
        start += size - overlap
    return chunks


def parsed_text(data: dict[str, Any]) -> str:
    pages = data.get("text_per_page", [])
    if isinstance(pages, list):
        return "\n".join(str(page) for page in pages)
    return str(pages)


def needs_deadline_follow_up(deadline: date, today: date, lead_days: int = 7) -> bool:
    days_left = (deadline - today).days
    return 0 <= days_left <= lead_days


class MatterIngestor:
    def __init__(self, client: InfraiClient, collection: str, embedding_model: str) -> None:
        self.client = client
        self.collection = collection
        self.embedding_model = embedding_model

    def ingest(self, intake: MatterIntake, today: date | None = None) -> IntakeResult:
        text = parsed_text(self.client.parse_pdf(intake.signed_pdf_base64))
        chunks = chunk_text(text)
        if not chunks:
            raise ValueError("The signed document did not contain indexable text")
        embeddings = self.client.embed(chunks, self.embedding_model)
        vectors = [
            {
                "id": self._vector_id(intake.matter_id, index),
                "values": embedding,
                "metadata": {
                    "matter_id": intake.matter_id,
                    "client_name": intake.client_name,
                    "chunk_index": index,
                    "signed_at": intake.signed_at.isoformat(),
                    "response_deadline": intake.response_deadline.isoformat(),
                    "text": chunk,
                },
            }
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings, strict=True))
        ]
        self.client.upsert(self.collection, vectors)
        decision_day = today or date.today()
        return IntakeResult(
            matter_id=intake.matter_id,
            delivery_status="signed_document_received",
            indexed_chunks=len(vectors),
            follow_up_required=needs_deadline_follow_up(intake.response_deadline, decision_day),
            follow_up_on=intake.response_deadline,
        )

    @staticmethod
    def _vector_id(matter_id: str, index: int) -> str:
        digest = hashlib.sha256(f"{matter_id}:{index}".encode()).hexdigest()[:24]
        return f"matter-{digest}"

