"""Chroma vector store. Every vector carries owner/document/page metadata, and every query is
filtered by owner (and optionally by document) before anything reaches the LLM."""

from dataclasses import dataclass
from functools import lru_cache

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

COLLECTION_NAME = "documind_chunks"


@dataclass
class Hit:
    vector_id: str
    chunk_id: int  # DocumentChunk.id in MySQL
    document_id: int
    page_number: int
    similarity: float  # cosine similarity, 1.0 = identical
    text: str


@lru_cache
def _client(path: str):
    return chromadb.PersistentClient(path=path, settings=ChromaSettings(anonymized_telemetry=False))


def _collection():
    path = settings.chroma_path
    path.mkdir(parents=True, exist_ok=True)
    return _client(str(path)).get_or_create_collection(COLLECTION_NAME, metadata={"hnsw:space": "cosine"}, embedding_function=None)


def vector_id_for(chunk_id: int) -> str:
    return f"chunk-{chunk_id}"


def add_chunks(*, user_id: int, document_id: int, chunk_ids: list[int], pages: list[int], texts: list[str], embeddings: list[list[float]]) -> list[str]:
    ids = [vector_id_for(c) for c in chunk_ids]
    metadatas = [{"user_id": user_id, "document_id": document_id, "page_number": p, "chunk_id": c} for p, c in zip(pages, chunk_ids)]
    _collection().add(ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas)
    return ids


def query(*, embedding: list[float], user_id: int, document_ids: list[int], k: int) -> list[Hit]:
    """Nearest chunks that belong to `user_id` AND to one of `document_ids`."""
    if not document_ids:
        return []
    where = {"$and": [{"user_id": {"$eq": user_id}}, {"document_id": {"$in": list(document_ids)}}]}
    result = _collection().query(query_embeddings=[embedding], n_results=k, where=where, include=["documents", "metadatas", "distances"])
    hits: list[Hit] = []
    for vid, doc, meta, dist in zip(result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0]):
        hits.append(
            Hit(
                vector_id=vid,
                chunk_id=int(meta["chunk_id"]),
                document_id=int(meta["document_id"]),
                page_number=int(meta["page_number"]),
                similarity=1.0 - float(dist),
                text=doc,
            )
        )
    return hits


def delete_document(document_id: int) -> None:
    _collection().delete(where={"document_id": {"$eq": document_id}})
