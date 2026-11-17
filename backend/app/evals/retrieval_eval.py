"""Retrieval quality on labelled queries (N4).

    python -m app.evals.retrieval_eval                       # all three modes
    python -m app.evals.retrieval_eval --modes bm25 hybrid

Metrics: hit@1 and hit@3 (a relevant chunk in the top 1 / 3) and MRR@10.
"""

import argparse
import json
from pathlib import Path
from typing import Any

from app.rag.chunking import Chunk
from app.rag.retriever import PolicyRetriever

QRELS_PATH = Path(__file__).resolve().parent / "retrieval_qrels.json"
MODES = ("bm25", "hybrid", "hybrid_rerank")


def load_qrels() -> list[dict[str, Any]]:
    return json.loads(QRELS_PATH.read_text(encoding="utf-8"))["queries"]


def is_relevant(chunk: Chunk, markers: list[str]) -> bool:
    text = chunk.labelled().lower()
    return any(marker.lower() in text for marker in markers)


def evaluate(retriever: PolicyRetriever, qrels: list[dict[str, Any]]) -> dict[str, Any]:
    hit1 = hit3 = reciprocal_ranks = 0.0
    misses = []
    for q in qrels:
        hits = retriever.search(q["merchant_id"], q["query"], top_k=10)
        rank = next((i + 1 for i, (chunk, _) in enumerate(hits) if is_relevant(chunk, q["relevant"])), None)
        hit1 += rank == 1
        hit3 += rank is not None and rank <= 3
        reciprocal_ranks += 1 / rank if rank else 0
        if not rank or rank > 3:
            misses.append({"merchant_id": q["merchant_id"], "query": q["query"], "rank": rank})
    n = len(qrels)
    return {
        "mode": retriever.mode,
        "queries": n,
        "hit@1": round(hit1 / n, 3),
        "hit@3": round(hit3 / n, 3),
        "mrr@10": round(reciprocal_ranks / n, 3),
        "misses": misses,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().splitlines()[0])
    parser.add_argument("--modes", nargs="+", default=list(MODES), choices=MODES)
    parser.add_argument("--show-misses", action="store_true")
    args = parser.parse_args(argv)
    qrels = load_qrels()
    print(f"{'mode':14} {'hit@1':>6} {'hit@3':>6} {'mrr@10':>7}   ({len(qrels)} queries)")
    for mode in args.modes:
        result = evaluate(PolicyRetriever(mode), qrels)
        print(f"{result['mode']:14} {result['hit@1']:>6} {result['hit@3']:>6} {result['mrr@10']:>7}")
        if args.show_misses:
            for miss in result["misses"]:
                print(f"    miss (rank {miss['rank']}): {miss['merchant_id']}: {miss['query']}")


if __name__ == "__main__":
    main()
