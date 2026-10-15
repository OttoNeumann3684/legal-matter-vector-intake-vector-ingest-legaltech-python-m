from __future__ import annotations

import os

from legal_intake.infrai_client import InfraiClient


def main() -> None:
    client = InfraiClient()
    try:
        result = client.create_collection(
            collection=os.getenv("INFRAI_COLLECTION", "legal-matters"),
            dimension=int(os.getenv("INFRAI_EMBEDDING_DIMENSION", "1536")),
        )
        print({"collection_status": "ready", "result": result})
    finally:
        client.close()


if __name__ == "__main__":
    main()

