import os
import re
from typing import List, Dict, Any

try:
    from rank_bm25 import BM25Okapi
except ImportError:
    BM25Okapi = None

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
except Exception:
    EMBEDDING_MODEL = None

DOCUMENTS_DIR = os.path.join(os.path.dirname(__file__), "documents")

class PolicyRetriever:
    def __init__(self, docs_dir: str = DOCUMENTS_DIR):
        self.docs_dir = docs_dir
        self.tenant_chunks: Dict[str, List[Dict[str, Any]]] = {}
        self._load_documents()

    def _load_documents(self):
        if not os.path.exists(self.docs_dir):
            return

        for filename in os.listdir(self.docs_dir):
            if filename.endswith(".md"):
                filepath = os.path.join(self.docs_dir, filename)
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract merchant_id from doc or filename
                merchant_match = re.search(r"Merchant ID: `([^`]+)`", content)
                if merchant_match:
                    merchant_id = merchant_match.group(1)
                else:
                    # fallback to filename slug prefix (e.g. 01_hotstar_policy.md -> hotstar)
                    merchant_id = filename.split("_")[1]

                # Chunk document by headers or double newlines
                chunks = self._chunk_text(content)
                self.tenant_chunks[merchant_id] = chunks

    def _chunk_text(self, text: str) -> List[Dict[str, Any]]:
        raw_sections = text.split("## ")
        chunks = []
        for i, sec in enumerate(raw_sections):
            if not sec.strip():
                continue
            section_title = sec.split("\n")[0].replace("#", "").strip()
            content = "## " + sec if i > 0 else sec
            chunks.append({
                "chunk_id": i,
                "title": section_title,
                "text": content.strip()
            })
        return chunks

    def retrieve_context(self, merchant_id: str, query: str, top_k: int = 2) -> List[str]:
        """
        Retrieve relevant policy chunks for a specific merchant_id using hybrid BM25 + dense search.
        """
        chunks = self.tenant_chunks.get(merchant_id, [])
        if not chunks:
            # Fallback search across all docs or return default string
            return ["No specific merchant policy found."]

        # BM25 Keyword Search
        tokenized_corpus = [c["text"].lower().split() for c in chunks]
        tokenized_query = query.lower().split()

        bm25_scores = []
        if BM25Okapi and tokenized_corpus:
            bm25 = BM25Okapi(tokenized_corpus)
            bm25_scores = bm25.get_scores(tokenized_query)

        # Dense Embedding Similarity (if sentence-transformers loaded)
        dense_scores = [0.0] * len(chunks)
        if EMBEDDING_MODEL:
            try:
                query_emb = EMBEDDING_MODEL.encode(query, convert_to_tensor=True)
                doc_embs = EMBEDDING_MODEL.encode([c["text"] for c in chunks], convert_to_tensor=True)
                from sentence_transformers import util
                sims = util.cos_sim(query_emb, doc_embs)[0].tolist()
                dense_scores = sims
            except Exception:
                pass

        # Combine Scores
        combined_results = []
        for idx, chunk in enumerate(chunks):
            bm25_score = bm25_scores[idx] if idx < len(bm25_scores) else 0.0
            dense_score = dense_scores[idx] if idx < len(dense_scores) else 0.0
            # Weighted hybrid score
            final_score = (0.4 * bm25_score) + (0.6 * dense_score)
            combined_results.append((final_score, chunk["text"]))

        combined_results.sort(key=lambda x: x[0], reverse=True)
        return [text for score, text in combined_results[:top_k]]

retriever = PolicyRetriever()
