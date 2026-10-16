import hashlib
import json
import math
import re
import uuid

import httpx

from app.config import Settings

COLLECTION = "DocumentPassage"
STOP = set(
    "a an the is are was were what which how much when who to of for in on and does do please me tell".split()
)


class Embedder:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.model = None

    def embed(self, texts: list[str], query=False) -> list[list[float]]:
        if self.settings.embedding_mode == "hash":
            # Deterministic offline demo/test double; this is not a learned embedding.
            vectors = []
            for text in texts:
                vector = [0.0] * 256
                for token in re.findall(r"\w+", text.lower()):
                    if token not in STOP:
                        vector[int(hashlib.sha256(token.encode()).hexdigest()[:8], 16) % 256] += 1
                length = math.sqrt(sum(v * v for v in vector)) or 1
                vectors.append([v / length for v in vector])
            return vectors
        if self.model is None:
            from fastembed import TextEmbedding

            self.model = TextEmbedding(
                self.settings.embedding_model,
                threads=2,
                cache_dir=str(self.settings.embedding_cache_dir),
            )
        function = self.model.query_embed if query else self.model.passage_embed
        return [vector.tolist() for vector in function(texts)]


def chunks(page: dict):
    # Bound model context and preserve page boundaries for every citation.
    # Keep original line breaks so an answer can cite a concise OCR line instead of the whole page.
    words = re.findall(r"\S+\s*", page["text"])
    for i in range(0, len(words), 180):
        text = "".join(words[i : i + 220]).strip()
        if text:
            yield i // 180, text


class WeaviateIndex:
    def __init__(self, settings: Settings, embedder=None, collection: str = COLLECTION):
        if not re.fullmatch(r"[A-Z][A-Za-z0-9_]{0,127}", collection):
            raise ValueError("Invalid Weaviate collection name")
        self.settings = settings
        self.embedder = embedder or Embedder(settings)
        self.collection = collection

    def ensure_schema(self):
        with httpx.Client(base_url=self.settings.weaviate_url, timeout=60) as client:
            response = client.get(f"/v1/schema/{self.collection}")
            if response.status_code == 200:
                return
            if response.status_code != 404:
                response.raise_for_status()
            response = client.post(
                "/v1/schema",
                json={
                    "class": self.collection,
                    "vectorizer": "none",
                    "properties": [
                        {"name": "documentId", "dataType": ["text"], "tokenization": "field"},
                        {"name": "filename", "dataType": ["text"]},
                        {"name": "page", "dataType": ["int"]},
                        {"name": "text", "dataType": ["text"]},
                    ],
                },
            )
            if response.status_code not in {200, 201}:
                # Another worker may have created the collection first.
                client.get(f"/v1/schema/{self.collection}").raise_for_status()

    def index(self, document: dict, pages: list[dict]):
        self.ensure_schema()
        with httpx.Client(base_url=self.settings.weaviate_url, timeout=90) as client:
            for page in pages:
                passages = list(chunks(page))
                vectors = self.embedder.embed([text for _, text in passages]) if passages else []
                for (ordinal, text), vector in zip(passages, vectors, strict=True):
                    object_id = str(
                        uuid.uuid5(uuid.NAMESPACE_URL, f"{document['id']}:{page['number']}:{ordinal}")
                    )
                    body = {
                        "class": self.collection,
                        "id": object_id,
                        "vector": vector,
                        "properties": {
                            "documentId": document["id"],
                            "filename": document["filename"],
                            "page": page["number"],
                            "text": text,
                        },
                    }
                    exists = client.head(f"/v1/objects/{self.collection}/{object_id}")
                    if exists.status_code == 404:
                        response = client.post("/v1/objects", json=body)
                    else:
                        exists.raise_for_status()
                        response = client.put(f"/v1/objects/{self.collection}/{object_id}", json=body)
                    response.raise_for_status()

    def search(self, question: str, limit: int = 5):
        vector = self.embedder.embed([question], query=True)[0]
        # All dynamic GraphQL strings use JSON encoding; no string interpolation of raw input.
        query = (
            f"{{Get{{{self.collection}(hybrid:{{query:{json.dumps(question)},vector:{json.dumps(vector)},"
            f"alpha:0.5}},limit:{limit}){{documentId filename page text _additional{{score}}}}}}}}"
        )
        with httpx.Client(base_url=self.settings.weaviate_url, timeout=60) as client:
            response = client.post("/v1/graphql", json={"query": query})
            response.raise_for_status()
            payload = response.json()
            if payload.get("errors"):
                raise RuntimeError("Search index is not ready")
            return payload["data"]["Get"][self.collection]


def evidence_answer(question: str, hits: list[dict], allowed_ids: set[str]):
    """Extractive answers: every displayed statement is an exact source excerpt."""
    tokens = set(re.findall(r"\w+", question.lower())) - STOP
    citations = []
    for hit in hits:
        if hit["documentId"] not in allowed_ids:
            continue
        sentences = re.split(r"(?<=[.!?])\s+|\n", hit["text"])
        ranked = sorted(
            sentences, key=lambda s: len(tokens & set(re.findall(r"\w+", s.lower()))), reverse=True
        )
        quote = ranked[0][:1200] if ranked else ""
        # No invented fallback when the retrieved passages share no meaningful terms.
        if not quote or not (tokens & set(re.findall(r"\w+", quote.lower()))):
            continue
        if any(c["document_id"] == hit["documentId"] and c["page"] == hit["page"] for c in citations):
            continue
        citations.append(
            {
                "id": len(citations) + 1,
                "document_id": hit["documentId"],
                "filename": hit["filename"],
                "page": hit["page"],
                "quote": quote,
            }
        )
    return {
        "answer": "\n\n".join(f"{c['quote']} [{c['id']}]" for c in citations)
        or "I could not find supporting evidence in the processed documents.",
        "citations": citations,
        "mode": "extractive",
        "question": question,
    }
