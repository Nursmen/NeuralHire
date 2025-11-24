# utils/embeddings.py
from sentence_transformers import SentenceTransformer, CrossEncoder
import re
import requests
import json

# Use multilingual-e5-small - designed for asymmetric search (query vs passage)
# Properly handles different text types with instruction prefixes
# 384 dimensions, excellent for Russian
_model = SentenceTransformer('intfloat/multilingual-e5-small')

# Cross-encoder for reranking - FREE, runs locally, much more accurate
# Using multilingual mMARCO model - specifically trained for multilingual retrieval
_reranker = None  # Lazy load to avoid startup cost

# Ollama settings for LLM validation
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"  # Small, fast, good for Russian. Alternatives: llama3.2:1b, phi3


def get_reranker():
    """Lazy load cross-encoder reranker."""
    global _reranker
    if _reranker is None:
        # Multilingual cross-encoder trained on mMARCO - much better for Russian
        _reranker = CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1')
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


def create_job_summary(title: str, knowledge: str, city: str = "", company: str = "") -> str:
    """Create a short summary for LLM validation."""
    parts = []
    if title:
        parts.append(title)
    if knowledge:
        # Take first 100 chars of knowledge
        parts.append(knowledge[:100])
    if company and company.lower() not in ('unknown', 'nan', 'none'):
        parts.append(f"({company})")
    if city and city.lower() not in ('unknown', 'nan', 'none'):
        parts.append(f"- {city}")
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


def llm_validate_results(query: str, job_summaries: list, top_k: int = 10) -> list:
    """
    Use local LLM (Ollama) to validate and rerank search results.
    FREE - runs completely locally via Ollama.

    Returns list of indices sorted by LLM's relevance ranking.
    Falls back gracefully if Ollama is not available.
    """
    if not job_summaries or len(job_summaries) == 0:
        return list(range(len(job_summaries)))

    # Build prompt for LLM
    jobs_text = "\n".join([f"{i+1}. {summary}" for i, summary in enumerate(job_summaries[:20])])

    prompt = f"""Ты помощник по поиску работы. Пользователь ищет: "{query}"

Вот список вакансий:
{jobs_text}

Выбери {min(top_k, len(job_summaries))} наиболее релевантных вакансий для запроса "{query}".
Ответь ТОЛЬКО номерами вакансий через запятую, от наиболее релевантной к менее релевантной.
Например: 3,1,5,2,4

Твой ответ (только номера):"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 100
                }
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json().get('response', '').strip()
            # Parse the numbers from response
            numbers = re.findall(r'\d+', result)
            indices = []
            seen = set()
            for num in numbers:
                idx = int(num) - 1  # Convert to 0-based index
                if 0 <= idx < len(job_summaries) and idx not in seen:
                    indices.append(idx)
                    seen.add(idx)
                if len(indices) >= top_k:
                    break

            # Add remaining indices that weren't mentioned
            for i in range(len(job_summaries)):
                if i not in seen and len(indices) < len(job_summaries):
                    indices.append(i)

            return indices[:top_k]
    except (requests.RequestException, json.JSONDecodeError, ValueError):
        # Ollama not available or error - fall back to original order
        pass

    # Fallback: return original order
    return list(range(min(top_k, len(job_summaries))))


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