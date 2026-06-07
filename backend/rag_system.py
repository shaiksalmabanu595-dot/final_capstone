"""
RAG System — ChromaDB vector + ES-BM25 + RRF fusion + Cross-Encoder reranker
"""
import os
import pickle
import numpy as np
import chromadb
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer, CrossEncoder
from rank_bm25 import BM25Okapi
import pandas as pd

EMBED_MODEL   = "all-MiniLM-L6-v2"
RERANK_MODEL  = "cross-encoder/ms-marco-MiniLM-L-6-v2"
CHROMA_PATH   = os.path.join(os.path.dirname(__file__), "data", "chroma_db")
BM25_PATH     = os.path.join(os.path.dirname(__file__), "data", "bm25_es.pkl")
DOCS_PATH     = os.path.join(os.path.dirname(__file__), "data", "documents.pkl")
COLLECTION    = "medical_equipment"


def _approx_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / 0.75))


def record_to_text(row: Dict) -> str:
    if row.get("machine_failure") == 1:
        failure_info = (
            f"FAILURE DETECTED: {row.get('failure_type', 'Unknown')} "
            f"(Severity: {row.get('severity', 'Unknown')}). "
            f"Downtime: {row.get('downtime_hours', 0)} hours. "
            f"Maintenance cost: ${row.get('maintenance_cost_usd', 0):,}. "
        )
    else:
        failure_info = "No failure detected during this inspection. "

    return (
        f"Equipment ID: {row.get('equipment_id')}. "
        f"Type: {row.get('equipment_type')}. "
        f"Model: {row.get('equipment_model')}. "
        f"Hospital Unit: {row.get('hospital_unit')}. "
        f"Date: {row.get('timestamp', '')}. "
        f"Air temperature: {row.get('air_temperature_k', 0):.1f}K. "
        f"Process temperature: {row.get('process_temperature_k', 0):.1f}K. "
        f"Rotational speed: {row.get('rotational_speed_rpm', 0)} RPM. "
        f"Torque: {row.get('torque_nm', 0):.1f} Nm. "
        f"Tool wear: {row.get('tool_wear_min', 0)} minutes. "
        f"Days since last PM: {row.get('days_since_last_pm', 0)}. "
        f"{failure_info}"
        f"Technician notes: {row.get('technician_notes', '')}."
    )


# ── ES-BM25 (Okapi BM25 with Elasticsearch defaults: k1=1.2, b=0.75) ─────────

class ESBM25:
    """BM25 with Elasticsearch-compatible parameters."""

    def __init__(self, tokenized_corpus: List[List[str]]):
        self._bm25 = BM25Okapi(tokenized_corpus, k1=1.2, b=0.75)

    def get_top_k(self, query_tokens: List[str], k: int) -> List[Tuple[int, float]]:
        scores = self._bm25.get_scores(query_tokens)
        top_idx = np.argsort(scores)[::-1][:k]
        return [(int(i), float(scores[i])) for i in top_idx if scores[i] > 0]


# ── RRF Fusion ────────────────────────────────────────────────────────────────

def rrf_fusion(
    ranked_lists: List[List[Tuple[int, float]]],
    k: int = 60,
) -> List[Tuple[int, float]]:
    """
    Reciprocal Rank Fusion.
    score(d) = Σ  1 / (k + rank(d))   for each retriever
    k=60 is the standard value from the original RRF paper.
    """
    scores: Dict[int, float] = {}
    for ranked in ranked_lists:
        for rank, (doc_id, _) in enumerate(ranked):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank + 1)
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)


# ── RAG System ────────────────────────────────────────────────────────────────

class RAGSystem:
    def __init__(self):
        print("Loading embedding model...")
        self.model = SentenceTransformer(EMBED_MODEL)

        print("Loading cross-encoder reranker...")
        try:
            self.reranker = CrossEncoder(RERANK_MODEL, max_length=512)
            self._reranker_ok = True
        except Exception as e:
            print(f"  Reranker unavailable ({e}), will use RRF scores directly.")
            self.reranker = None
            self._reranker_ok = False

        self.chroma = chromadb.PersistentClient(path=CHROMA_PATH)
        self.collection = None
        self.bm25: ESBM25 = None
        self.documents: List[Dict] = []
        self.doc_texts: List[str] = []
        self.is_built = False

    # ── Index building ─────────────────────────────────────────────────────────

    def build_index(self, df: pd.DataFrame, force_rebuild: bool = False):
        os.makedirs(CHROMA_PATH, exist_ok=True)

        if not force_rebuild and self._load_cached():
            print("Loaded RAG index from cache.")
            return

        print(f"Building RAG index from {len(df)} records...")
        self.documents = df.to_dict(orient="records")
        self.doc_texts = [record_to_text(row) for row in self.documents]

        # ── ChromaDB collection ────────────────────────────────────────────────
        print("Building ChromaDB collection...")
        try:
            self.chroma.delete_collection(COLLECTION)
        except Exception:
            pass

        self.collection = self.chroma.create_collection(
            name=COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

        print("Generating embeddings and adding to ChromaDB...")
        embeddings = self.model.encode(
            self.doc_texts, show_progress_bar=True, batch_size=64
        ).astype(np.float32)

        batch_size = 500
        for i in range(0, len(self.doc_texts), batch_size):
            end = i + batch_size
            self.collection.add(
                ids=[str(j) for j in range(i, min(end, len(self.doc_texts)))],
                embeddings=embeddings[i:end].tolist(),
                documents=self.doc_texts[i:end],
            )

        # ── ES-BM25 index ──────────────────────────────────────────────────────
        print("Building ES-BM25 index (k1=1.2, b=0.75)...")
        tokenized = [t.lower().split() for t in self.doc_texts]
        self.bm25 = ESBM25(tokenized)

        self._save_cache()
        self.is_built = True
        print("RAG index built and cached.")

    def _save_cache(self):
        with open(BM25_PATH, "wb") as f:
            pickle.dump(self.bm25, f)
        with open(DOCS_PATH, "wb") as f:
            pickle.dump((self.documents, self.doc_texts), f)

    def _load_cached(self) -> bool:
        try:
            self.collection = self.chroma.get_collection(COLLECTION)
            if self.collection.count() == 0:
                return False
        except Exception:
            return False

        if os.path.exists(BM25_PATH) and os.path.exists(DOCS_PATH):
            try:
                with open(BM25_PATH, "rb") as f:
                    self.bm25 = pickle.load(f)
                with open(DOCS_PATH, "rb") as f:
                    self.documents, self.doc_texts = pickle.load(f)
                self.is_built = True
                return True
            except Exception as e:
                print(f"Cache load failed: {e}")
        return False

    # ── Retrieval ──────────────────────────────────────────────────────────────

    def vector_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """ChromaDB cosine-similarity search using our own embeddings."""
        query_emb = self.model.encode([query]).astype(np.float32).tolist()
        n = min(k, self.collection.count())
        res = self.collection.query(query_embeddings=query_emb, n_results=n)
        ids = res["ids"][0]
        # ChromaDB cosine space returns distance = 1 - cos_sim  → sim = 1 - dist
        dists = res["distances"][0]
        return [(int(doc_id), round(1.0 - dist, 6)) for doc_id, dist in zip(ids, dists)]

    def bm25_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        """ES-BM25 retrieval (k1=1.2, b=0.75)."""
        tokens = query.lower().split()
        return self.bm25.get_top_k(tokens, k)

    # ── Cross-Encoder Reranker ─────────────────────────────────────────────────

    def rerank(
        self,
        query: str,
        candidates: List[Tuple[int, float]],
        k: int,
        **_,
    ) -> List[Tuple[int, float]]:
        """Cross-encoder reranking using ms-marco-MiniLM-L-6-v2."""
        if not candidates:
            return []
        if not self._reranker_ok:
            return candidates[:k]

        pairs = [(query, self.doc_texts[idx]) for idx, _ in candidates]
        scores = self.reranker.predict(pairs, show_progress_bar=False)
        reranked = [(candidates[i][0], float(scores[i])) for i in range(len(candidates))]
        return sorted(reranked, key=lambda x: x[1], reverse=True)[:k]

    # ── Hybrid Search (ChromaDB + ES-BM25 + RRF + Cross-Encoder) ──────────────

    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.6,        # kept for API compatibility; RRF is now used
        filters: Dict[str, Any] = None,
        use_reranking: bool = True,
    ) -> List[Dict]:
        candidate_k = k * 6

        # Phase 1: Dual retrieval
        vector_results = self.vector_search(query, k=candidate_k)
        bm25_results   = self.bm25_search(query,   k=candidate_k)

        # Phase 2: RRF fusion (replaces alpha-weighted linear combination)
        ranked = rrf_fusion([vector_results, bm25_results])

        # Phase 3: Cross-encoder reranking on top candidate pool
        if use_reranking and self._reranker_ok:
            top_candidates = ranked[: k * 4]
            ranked = self.rerank(query, top_candidates, k=k * 4)

        # Phase 4: Metadata filtering + final selection
        results = []
        for idx, score in ranked:
            doc = self.documents[idx].copy()
            doc["relevance_score"] = round(score, 4)
            doc["document_text"]   = self.doc_texts[idx]

            if filters:
                if filters.get("equipment_type"):
                    if doc.get("equipment_type", "").lower() != filters["equipment_type"].lower():
                        continue
                if filters.get("hospital_unit"):
                    if doc.get("hospital_unit", "").lower() != filters["hospital_unit"].lower():
                        continue
                if filters.get("severity"):
                    if doc.get("severity", "").lower() != filters["severity"].lower():
                        continue
                if filters.get("failure_only"):
                    if doc.get("machine_failure", 0) != 1:
                        continue

            results.append(doc)
            if len(results) >= k:
                break

        return results

    # ── Token-aware context builder ────────────────────────────────────────────

    def get_context_for_llm(
        self,
        retrieved_docs: List[Dict],
        max_tokens: int = 1200,
    ) -> Tuple[str, Dict]:
        context_parts = []
        total_tokens  = 0
        skipped       = 0
        for i, doc in enumerate(retrieved_docs):
            text      = f"[Incident {i+1}] {doc['document_text']}"
            est_toks  = _approx_tokens(text)
            if total_tokens + est_toks > max_tokens:
                skipped += 1
                continue
            context_parts.append(text)
            total_tokens += est_toks

        token_info = {
            "included_docs":    len(context_parts),
            "skipped_docs":     skipped,
            "estimated_tokens": total_tokens,
            "token_budget":     max_tokens,
            "utilization_pct":  round(total_tokens / max_tokens * 100, 1),
        }
        return "\n\n".join(context_parts), token_info


# ── Singleton ─────────────────────────────────────────────────────────────────

_rag_instance: RAGSystem = None


def get_rag_system() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
    return _rag_instance
