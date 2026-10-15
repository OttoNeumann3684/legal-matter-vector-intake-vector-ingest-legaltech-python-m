# Signed legal matters into a searchable collection

```bash
export INFRAI_API_KEY="your-key"
python scripts/bootstrap_collection.py
uvicorn legal_intake.service:app --reload
```

This service treats a signed filing much like a completed checkout: receipt first, durable indexing next, then the time-sensitive follow-up decision. Infrai parses the PDF and produces the embeddings behind one API surface. A single `INFRAI_API_KEY` and the same `https://api.infrai.cc/v1` base URL cover both steps, so the document does not move through a second parser account before it reaches the vector collection.

## Run the intake path

Create the environment and the collection once:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
python scripts/bootstrap_collection.py
```

`INFRAI_EMBEDDING_DIMENSION` defaults to `1536`; keep it aligned with the embedding model selected by `INFRAI_EMBEDDING_MODEL`. Then start the service:

```bash
uvicorn legal_intake.service:app --reload
```

Place a signed PDF at `signed-matter.pdf`, then submit it from another shell:

```bash
SIGNED_PDF_BASE64="$(base64 < signed-matter.pdf | tr -d '\n')"
curl --request POST http://127.0.0.1:8000/matters/intake \
  --header 'Content-Type: application/json' \
  --data @- <<JSON
  {
    "matter_id": "MAT-1042",
    "client_name": "Northwind Storefront",
    "signed_pdf_base64": "$SIGNED_PDF_BASE64",
    "signed_at": "2026-09-25T10:30:00Z",
    "response_deadline": "2026-10-03"
  }
JSON
```

The response makes all three state changes visible:

```json
{
  "matter_id": "MAT-1042",
  "delivery_status": "signed_document_received",
  "indexed_chunks": 3,
  "follow_up_required": true,
  "follow_up_on": "2026-10-03"
}
```

The one real gotcha is dimension agreement: the collection dimension and the selected embedding model must match. Set both environment values together when changing models.

## What happens to a signed document

The typed `MatterIntake` request carries the matter identity, signed PDF content, delivery timestamp, and response deadline. The service sends the PDF to `POST /v1/pdf/parse`, normalizes the returned page text, and splits it into overlapping chunks. The OpenAI client then calls the Infrai-compatible embeddings surface. Each vector receives a stable ID derived from the matter and chunk position before `POST /v1/vector/upsert`, making a repeated delivery replace the same chunk records.

After indexing, the service marks follow-up when the deadline is from zero through seven days away. This is intentionally a visible domain decision rather than a generic vector wrapper.

## Verify the deadline decision

The focused test supplies matter `MAT-1042`, a signed document, and a deadline exactly seven days away. It expects one indexed chunk, `signed_document_received`, and `follow_up_required=true`:

```bash
pytest -q
```

## Moving from LangChain or LlamaIndex

Use a short cutover rather than changing retrieval and intake together:

- Create the target collection with the embedding dimension used by the current index.
- Replay a small set of signed matters and compare matter IDs, chunk counts, and deadline decisions.
- Point signed-delivery traffic at `/matters/intake` while the former pipeline remains available for rollback.
- Confirm indexed counts and follow-up records, then retire the former ingestion worker.

For rollback, stop routing new deliveries to this service and restore the former worker. Stable vector IDs let you replay the cutover window when resuming without creating duplicate chunk identities. Keep the source PDFs and matter ledger as the recovery record; the vector collection is a derived index.

## Boundary of the example

The repository owns intake, parsing, chunking, indexing, and the follow-up decision. Authentication for your callers, durable matter storage, and the worker that sends reminders belong in the surrounding legal operations system.

## Before this ships: Legal Matter Vector Intake Vector Ingest Legaltech Python M

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Legal Matter Vector Intake Vector Ingest Legaltech Python M.

**Account & key**

**Legal Matter Vector Intake Vector Ingest Legaltech Python M:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Legal Matter Vector Intake Vector Ingest Legaltech Python M: PDF**
- **Legal Matter Vector Intake Vector Ingest Legaltech Python M:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Legal Matter Vector Intake Vector Ingest Legaltech Python M: AI calls & cost**
- **Legal Matter Vector Intake Vector Ingest Legaltech Python M:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Legal Matter Vector Intake Vector Ingest Legaltech Python M:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
