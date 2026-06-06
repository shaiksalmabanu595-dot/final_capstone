import os
import numpy as np
import faiss
import pickle
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from rank_bm25 import BM25Okapi
import pandas as pd

MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_PATH = os.path.join(os.path.dirname(__file__), "data", "faiss_index.bin")
BM25_PATH  = os.path.join(os.path.dirname(__file__), "data", "bm25.pkl")
DOCS_PATH  = os.path.join(os.path.dirname(__file__), "data", "documents.pkl")
EMBS_PATH  = os.path.join(os.path.dirname(__file__), "data", "embeddings.npy")

# Approximate tokens from word count (English technical text ≈ 0.75 words/token)
def _approx_tokens(text: str) -> int:
    return max(1, int(len(text.split()) / 0.75))


def record_to_text(row: Dict) -> str:
    failure_info = ""
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


class RAGSystem:
    def __init__(self):
        print("Loading embedding model...")
        self.model = SentenceTransformer(MODEL_NAME)
        self.index: faiss.Index = None
        self.bm25: BM25Okapi = None
        self.documents: List[Dict] = []
        self.doc_texts: List[str] = []
        self.embeddings: np.ndarray = None  # stored for reranking
        self.is_built = False

    def build_index(self, df: pd.DataFrame, force_rebuild: bool = False):
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)

        if not force_rebuild and self._load_cached():
            print("Loaded RAG index from cache.")
            return

        print(f"Building RAG index from {len(df)} records...")
        self.documents = df.to_dict(orient="records")
        self.doc_texts = [record_to_text(row) for row in self.documents]

        # Generate embeddings
        print("Generating embeddings...")
        embeddings = self.model.encode(self.doc_texts, show_progress_bar=True, batch_size=64)
        embeddings = embeddings.astype(np.float32)
        faiss.normalize_L2(embeddings)
        self.embeddings = embeddings  # keep for reranking

        # Build FAISS index
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)  # Inner product (cosine after normalization)
        self.index.add(embeddings)

        # Build BM25 index
        tokenized = [text.lower().split() for text in self.doc_texts]
        self.bm25 = BM25Okapi(tokenized)

        self._save_cache()
        self.is_built = True
        print("RAG index built and cached.")

    def _save_cache(self):
        faiss.write_index(self.index, INDEX_PATH)
        np.save(EMBS_PATH, self.embeddings)
        with open(BM25_PATH, "wb") as f:
            pickle.dump(self.bm25, f)
        with open(DOCS_PATH, "wb") as f:
            pickle.dump((self.documents, self.doc_texts), f)

    def _load_cached(self) -> bool:
        if os.path.exists(INDEX_PATH) and os.path.exists(BM25_PATH) and os.path.exists(DOCS_PATH):
            try:
                self.index = faiss.read_index(INDEX_PATH)
                with open(BM25_PATH, "rb") as f:
                    self.bm25 = pickle.load(f)
                with open(DOCS_PATH, "rb") as f:
                    self.documents, self.doc_texts = pickle.load(f)
                # Load stored embeddings if available (needed for reranking)
                if os.path.exists(EMBS_PATH):
                    self.embeddings = np.load(EMBS_PATH)
                self.is_built = True
                return True
            except Exception as e:
                print(f"Cache load failed: {e}")
        return False

    def vector_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        query_emb = self.model.encode([query]).astype(np.float32)
        faiss.normalize_L2(query_emb)
        scores, indices = self.index.search(query_emb, k)
        return [(int(idx), float(score)) for idx, score in zip(indices[0], scores[0]) if idx >= 0]

    def bm25_search(self, query: str, k: int = 10) -> List[Tuple[int, float]]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:k]
        return [(int(idx), float(scores[idx])) for idx in top_indices if scores[idx] > 0]

    # ── Embedding-based Reranking ─────────────────────────────────────────────
    def rerank(
        self,
        query: str,
        candidates: List[Tuple[int, float]],
        k: int,
        query_terms: List[str] = None,
    ) -> List[Tuple[int, float]]:
        """
        Reranking using maintenance embeddings.

        After hybrid retrieval, compute a fine-grained rerank score that combines:
          1. Embedding cosine similarity (query_emb · doc_emb) — re-computed precisely
          2. Metadata relevance bonus (equipment type / failure type keyword match)
          3. Recency bonus (prefer more recent incidents)

        This is the "maintenance embeddings reranking" step required by Req 2.
        """
        if self.embeddings is None or not candidates:
            return candidates[:k]

        # Encode query with normalization (same pipeline as index-time)
        query_emb = self.model.encode([query]).astype(np.float32)[0]
        query_emb /= np.linalg.norm(query_emb) + 1e-9

        query_lower = query.lower()
        terms = query_terms or query_lower.split()

        reranked = []
        for idx, initial_score in candidates:
            doc = self.documents[idx]

            # 1. Precise cosine similarity against stored embedding
            doc_emb = self.embeddings[idx]
            cosine_sim = float(np.dot(query_emb, doc_emb))

            # 2. Metadata relevance: equipment type / failure type keyword match
            meta_bonus = 0.0
            eq_type = doc.get("equipment_type", "").lower()
            fail_type = doc.get("failure_type", "").lower()
            unit = doc.get("hospital_unit", "").lower()
            severity = doc.get("severity", "").lower()

            if any(t in eq_type or t in eq_type.replace(" ", "") for t in terms):
                meta_bonus += 0.08
            if any(t in fail_type for t in terms):
                meta_bonus += 0.06
            if any(t in unit for t in terms):
                meta_bonus += 0.04
            if doc.get("machine_failure") == 1:
                if "fail" in query_lower or "break" in query_lower or "error" in query_lower:
                    meta_bonus += 0.05
            if severity in ("critical", "high") and (
                "critical" in query_lower or "urgent" in query_lower or "emergency" in query_lower
            ):
                meta_bonus += 0.04

            # 3. Recency bonus (tool wear as proxy for recent activity)
            tool_wear = doc.get("tool_wear_min", 0)
            recency_bonus = min(0.03, tool_wear / 10000.0)

            # Final rerank score: weighted combination
            final_score = 0.65 * cosine_sim + 0.25 * initial_score + meta_bonus + recency_bonus
            reranked.append((idx, round(final_score, 6)))

        return sorted(reranked, key=lambda x: x[1], reverse=True)[:k]

    # ── Hybrid Search ─────────────────────────────────────────────────────────
    def hybrid_search(
        self,
        query: str,
        k: int = 5,
        alpha: float = 0.6,
        filters: Dict[str, Any] = None,
        use_reranking: bool = True,
    ) -> List[Dict]:
        # Phase 1: Retrieve candidates (wider pool for reranking)
        candidate_k = k * 6
        vector_results = self.vector_search(query, k=candidate_k)
        bm25_results = self.bm25_search(query, k=candidate_k)

        # Phase 2: Normalize and combine (RRF-style normalization)
        def normalize(results):
            if not results:
                return {}
            max_score = max(s for _, s in results) or 1.0
            return {idx: s / max_score for idx, s in results}

        v_scores = normalize(vector_results)
        b_scores = normalize(bm25_results)

        all_indices = set(v_scores) | set(b_scores)
        combined = {
            idx: alpha * v_scores.get(idx, 0.0) + (1 - alpha) * b_scores.get(idx, 0.0)
            for idx in all_indices
        }
        ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)

        # Phase 3: Embedding-based reranking on top candidates
        if use_reranking and self.embeddings is not None:
            top_candidates = ranked[: k * 4]  # rerank a wider pool
            ranked = self.rerank(query, top_candidates, k=k * 4)

        # Phase 4: Metadata filtering + final selection
        results = []
        for idx, score in ranked:
            doc = self.documents[idx].copy()
            doc["relevance_score"] = round(score, 4)
            doc["document_text"] = self.doc_texts[idx]

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

    # ── Token-aware context builder ───────────────────────────────────────────
    def get_context_for_llm(
        self,
        retrieved_docs: List[Dict],
        max_tokens: int = 1200,
    ) -> Tuple[str, Dict]:
        """
        Build LLM context string from retrieved docs.
        Respects a token budget (approx tokens, not chars).
        Returns (context_string, token_usage_info).
        """
        context_parts = []
        total_tokens = 0
        skipped = 0
        for i, doc in enumerate(retrieved_docs):
            text = f"[Incident {i+1}] {doc['document_text']}"
            est_tokens = _approx_tokens(text)
            if total_tokens + est_tokens > max_tokens:
                skipped += 1
                continue
            context_parts.append(text)
            total_tokens += est_tokens

        token_info = {
            "included_docs": len(context_parts),
            "skipped_docs": skipped,
            "estimated_tokens": total_tokens,
            "token_budget": max_tokens,
            "utilization_pct": round(total_tokens / max_tokens * 100, 1),
        }
        return "\n\n".join(context_parts), token_info


# Singleton
_rag_instance: RAGSystem = None


def get_rag_system() -> RAGSystem:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGSystem()
    return _rag_instance
