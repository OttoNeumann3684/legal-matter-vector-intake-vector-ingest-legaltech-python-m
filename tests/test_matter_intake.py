from datetime import date, datetime, timezone

from legal_intake.matter_intake import MatterIngestor, MatterIntake


class RecordingClient:
    def __init__(self) -> None:
        self.vectors: list[dict[str, object]] = []

    def parse_pdf(self, pdf: str) -> dict[str, object]:
        assert pdf == "signed-pdf-data"
        return {"text_per_page": ["Answer due October 3. Counsel must respond."]}

    def embed(self, texts: list[str], model: str) -> list[list[float]]:
        assert model == "text-embedding-3-small"
        return [[0.25, 0.75] for _ in texts]

    def upsert(self, collection: str, vectors: list[dict[str, object]]) -> dict[str, object]:
        assert collection == "legal-matters"
        self.vectors = vectors
        return {"upserted": len(vectors)}


def test_signed_delivery_is_indexed_and_near_deadline_is_flagged() -> None:
    client = RecordingClient()
    intake = MatterIntake(
        matter_id="MAT-1042",
        client_name="Northwind Storefront",
        signed_pdf_base64="signed-pdf-data",
        signed_at=datetime(2026, 9, 25, 10, 30, tzinfo=timezone.utc),
        response_deadline=date(2026, 10, 3),
    )

    result = MatterIngestor(client, "legal-matters", "text-embedding-3-small").ingest(
        intake,
        today=date(2026, 9, 26),
    )

    assert result.delivery_status == "signed_document_received"
    assert result.indexed_chunks == 1
    assert result.follow_up_required is True
    assert client.vectors[0]["metadata"]["matter_id"] == "MAT-1042"

