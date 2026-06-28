import numpy as np
import faiss
from rank_bm25 import BM25Okapi
from src.client import get_embedding

RRF_K = 60


def build_chunks(extraction: dict) -> list[str]:
    chunks = []
    chunks.append(
        f"Patient: {extraction.get('patient_name', 'Unknown')} | "
        f"Report Date: {extraction.get('report_date', 'Unknown')}"
    )
    for ind in extraction.get("indicators", []):
        chunk = (
            f"{ind['name']}: {ind['value']} {ind.get('unit', '')} | "
            f"Reference: {ind.get('reference_range', 'N/A')} | "
            f"Status: {ind.get('status', 'unknown')} | "
            f"Note: {ind.get('note', '')}"
        ).strip()
        chunks.append(chunk)
    return chunks


def _rrf(ranked_lists: list[list[int]], k: int) -> list[int]:
    scores = {}
    for ranked in ranked_lists:
        for rank, idx in enumerate(ranked):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)[:k]


class PatientIndex:
    def __init__(self, chunks: list[str]):
        self.chunks = chunks
        self._build_bm25(chunks)
        self._build_faiss(chunks)

    def _build_bm25(self, chunks: list[str]):
        tokenized = [c.lower().split() for c in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def _build_faiss(self, chunks: list[str]):
        vectors = np.array([get_embedding(c) for c in chunks], dtype="float32")
        faiss.normalize_L2(vectors)
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def search(self, query: str, k: int = 5) -> list[str]:
        q_vec = np.array([get_embedding(query)], dtype="float32")
        faiss.normalize_L2(q_vec)
        _, ids = self.index.search(q_vec, k)
        dense_ranked = [i for i in ids[0] if i >= 0]

        bm25_scores = self.bm25.get_scores(query.lower().split())
        sparse_ranked = list(np.argsort(bm25_scores)[::-1][:k])

        merged = _rrf([dense_ranked, sparse_ranked], k)
        return [self.chunks[i] for i in merged]