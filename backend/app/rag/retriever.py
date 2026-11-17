"""Per-merchant policy retrieval.

RAG_MODE:
- bm25:          keyword ranking only (no models; used by tests and as the fallback)
- hybrid:        BM25 + dense embeddings (BAAI/bge-small-en-v1.5), fused with reciprocal-rank fusion
- hybrid_rerank: hybrid candidates re-scored by a cross-encoder (Xenova/ms-marco-MiniLM-L-6-v2)

Models run locally on ONNX Runtime via fastembed (no PyTorch). If they can't load, retrieval
degrades to BM25 and logs why, rather than failing requests.
"""

import logging
import re

import numpy as np
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.rag.chunking import Chunk, load_corpus

logger = logging.getLogger(__name__)

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
RERANK_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"
CANDIDATES = 10  # per ranker, before fusion
# Small batches: ONNX Runtime's memory arena grows to the largest batch it has seen (batch 256 peaked at
# ~2 GB; batch 8 at ~350 MB).
EMBED_BATCH = 8
RRF_K = 60
NOT_FOUND = "No specific merchant policy found."

_STOPWORDS = set(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "for",
        "in",
        "on",
        "at",
        "by",
        "with",
        "is",
        "are",
        "was",
        "be",
        "can",
        "i",
        "my",
        "me",
        "we",
        "our",
        "you",
        "your",
        "it",
        "this",
        "that",
        "do",
        "does",
        "please",
        "would",
        "could",
        "should",
        "will",
        "what",
        "how",
    ]
)


def tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOPWORDS]


def reciprocal_rank_fusion(rankings: list[list[int]], k: int = RRF_K) -> list[int]:
    scores: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            scores[idx] = scores.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores, key=lambda idx: scores[idx], reverse=True)


class PolicyRetriever:
    def __init__(self, mode: str | None = None):
        self.corpus = load_corpus()
        self.mode = mode or settings.RAG_MODE
        self._bm25 = {
            m: BM25Okapi([tokenize(c.labelled()) for c in chunks]) for m, chunks in self.corpus.items()
        }
        self._embedder = None
        self._reranker = None
        self._vectors: dict[str, np.ndarray] = {}
        if self.mode != "bm25":
            self._load_models()

    @property
    def tenant_chunks(self) -> dict[str, list[Chunk]]:
        return self.corpus

    def _load_models(self) -> None:
        try:
            from fastembed import TextEmbedding
            from fastembed.rerank.cross_encoder import TextCrossEncoder

            self._embedder = TextEmbedding(
                EMBEDDING_MODEL, cache_dir=settings.MODEL_CACHE_DIR, threads=settings.RAG_THREADS
            )
            for merchant_id, chunks in self.corpus.items():
                self._vectors[merchant_id] = self._normalise(
                    np.array(
                        list(self._embedder.embed([c.labelled() for c in chunks], batch_size=EMBED_BATCH))
                    )
                )
            if self.mode == "hybrid_rerank":
                self._reranker = TextCrossEncoder(
                    RERANK_MODEL, cache_dir=settings.MODEL_CACHE_DIR, threads=settings.RAG_THREADS
                )
        except Exception:
            logger.exception("Dense retrieval models unavailable; falling back to BM25")
            self.mode, self._embedder, self._reranker, self._vectors = "bm25", None, None, {}

    @staticmethod
    def _normalise(vectors: np.ndarray) -> np.ndarray:
        return vectors / np.clip(np.linalg.norm(vectors, axis=-1, keepdims=True), 1e-12, None)

    def search(self, merchant_id: str, query: str, top_k: int = 3) -> list[tuple[Chunk, float]]:
        chunks = self.corpus.get(merchant_id)
        if not chunks:
            return []
        bm25_scores = self._bm25[merchant_id].get_scores(tokenize(query))
        rankings = [[int(i) for i in np.argsort(-bm25_scores)[:CANDIDATES]]]
        if self._embedder is not None:
            query_vec = self._normalise(np.array(list(self._embedder.embed([query])))[0])
            dense = self._vectors[merchant_id] @ query_vec
            rankings.append([int(i) for i in np.argsort(-dense)[:CANDIDATES]])

        candidates = reciprocal_rank_fusion(rankings)[: max(top_k, 8)]
        if self._reranker is not None:
            scores = list(
                self._reranker.rerank(
                    query, [chunks[i].labelled() for i in candidates], batch_size=EMBED_BATCH
                )
            )
            ranked = sorted(zip(candidates, scores, strict=True), key=lambda pair: pair[1], reverse=True)
        else:
            ranked = [(i, float(bm25_scores[i])) for i in candidates]
        return [(chunks[i], float(score)) for i, score in ranked[:top_k]]

    def retrieve_context(self, merchant_id: str, query: str, top_k: int = 2) -> list[str]:
        hits = self.search(merchant_id, query, top_k)
        return [chunk.labelled() for chunk, _ in hits] or [NOT_FOUND]


retriever = PolicyRetriever()
