# utils/embeddings.py
from sentence_transformers import SentenceTransformer, CrossEncoder
import re

# Use multilingual-e5-small - designed for asymmetric search (query vs passage)
# Properly handles different text types with instruction prefixes
# 384 dimensions, excellent for Russian
_model = SentenceTransformer('intfloat/multilingual-e5-small')

# Cross-encoder for reranking - FREE, runs locally, much more accurate
# This model scores query-document pairs directly (not via embeddings)
_reranker = None  # Lazy load to avoid startup cost


def get_reranker():
    """Lazy load cross-encoder reranker."""
    global _reranker
    if _reranker is None:
        # Multilingual cross-encoder, great for Russian
        _reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    return _reranker


def preprocess_text(text: str) -> str:
    """Clean and normalize text for better embedding quality."""
    if not text:
        return ""

    text = str(text).strip()
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    # Keep alphanumeric, Russian chars, and basic punctuation
    text = re.sub(r'[^\w\s\-.,;:!?/()+#А-Яа-яЁё]+', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def create_job_text(title: str, knowledge: str, city: str = "",
                    company: str = "", additions: str = "") -> str:
    """Create combined text for job embedding - simple concatenation."""
    parts = []

    title_clean = preprocess_text(title)
    if title_clean:
        parts.append(title_clean)

    knowledge_clean = preprocess_text(knowledge)
    if knowledge_clean:
        parts.append(knowledge_clean)

    city_clean = preprocess_text(city)
    if city_clean and city_clean.lower() not in ('unknown', 'неизвестно', 'nan', 'none'):
        parts.append(city_clean)

    company_clean = preprocess_text(company)
    if company_clean and company_clean.lower() not in ('unknown', 'неизвестно', 'nan', 'none'):
        parts.append(company_clean)

    additions_clean = preprocess_text(additions)
    if additions_clean and additions_clean not in ('[]', ''):
        additions_clean = additions_clean.replace('[', '').replace(']', '').replace("'", "")
        if additions_clean.strip():
            parts.append(additions_clean)

    return " ".join(parts)


def embed_text(text: str):
    """Embed a single text string (generic)."""
    if not text or not text.strip():
        return None

    cleaned = preprocess_text(text)
    if not cleaned:
        return None

    # e5 models require "passage: " prefix for documents
    return _model.encode(f"passage: {cleaned}", normalize_embeddings=True).tolist()


def embed_job(title: str, knowledge: str, city: str = "",
              company: str = "", additions: str = ""):
    """Create embedding for a job posting."""
    combined_text = create_job_text(title, knowledge, city, company, additions)

    if not combined_text:
        return None

    # e5 models require "passage: " prefix for documents being searched
    return _model.encode(f"passage: {combined_text}", normalize_embeddings=True).tolist()


def embed_query(query: str):
    """Create embedding for a user search query."""
    if not query or not query.strip():
        return None

    cleaned = preprocess_text(query)
    if not cleaned:
        return None

    # e5 models require "query: " prefix for search queries
    return _model.encode(f"query: {cleaned}", normalize_embeddings=True).tolist()


def rerank_results(query: str, job_texts: list, top_k: int = 20) -> list:
    """
    Rerank job results using cross-encoder for better accuracy.
    Returns list of (index, score) sorted by relevance.
    FREE - runs locally, no API costs.
    """
    if not job_texts:
        return []

    reranker = get_reranker()
    query_clean = preprocess_text(query)

    # Create pairs for cross-encoder
    pairs = [[query_clean, text] for text in job_texts]

    # Get reranking scores
    scores = reranker.predict(pairs)

    # Sort by score descending
    indexed_scores = list(enumerate(scores))
    indexed_scores.sort(key=lambda x: x[1], reverse=True)

    return indexed_scores[:top_k]


def compute_keyword_boost(query: str, job_text: str) -> float:
    """
    Compute keyword overlap boost for better matching.
    Returns a boost factor based on exact keyword matches.
    """
    query_words = set(preprocess_text(query).lower().split())
    job_words = set(preprocess_text(job_text).lower().split())

    if not query_words:
        return 0.0

    # Count matching words
    matches = query_words & job_words
    # Boost based on percentage of query words found
    return len(matches) / len(query_words)


def embed_texts_batch(texts):
    """Batch embed multiple texts (as passages)."""
    cleaned_texts = [preprocess_text(t) for t in texts]
    valid_indices = [i for i, t in enumerate(cleaned_texts) if t]
    valid_texts = [f"passage: {cleaned_texts[i]}" for i in valid_indices]

    if not valid_texts:
        return [None] * len(texts)

    embeddings = _model.encode(valid_texts, normalize_embeddings=True, show_progress_bar=True).tolist()

    results = [None] * len(texts)
    for idx, emb in zip(valid_indices, embeddings):
        results[idx] = emb

    return results