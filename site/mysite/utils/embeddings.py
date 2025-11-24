# utils/embeddings.py
from sentence_transformers import SentenceTransformer
import re

# Use multilingual model - much better for Russian text
# paraphrase-multilingual-MiniLM-L12-v2: 384 dimensions, supports 50+ languages including Russian
_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')


def preprocess_text(text: str) -> str:
    """
    Clean and normalize text for better embedding quality.
    """
    if not text:
        return ""

    # Convert to string and strip
    text = str(text).strip()

    # Normalize whitespace (multiple spaces, tabs, newlines -> single space)
    text = re.sub(r'\s+', ' ', text)

    # Remove excessive punctuation but keep meaningful ones
    text = re.sub(r'[^\w\s\-.,;:!?/()]+', ' ', text)

    # Remove very short tokens (1 char) that are likely noise, except common ones
    words = text.split()
    words = [w for w in words if len(w) > 1 or w.lower() in ('c', 'c#', 'r', 'c++')]
    text = ' '.join(words)

    # Final cleanup
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def create_job_embedding_text(title: str, knowledge: str, city: str = "",
                               company: str = "", additions: str = "") -> str:
    """
    Create a rich, structured text for job embeddings.
    Title is given more weight by repetition.
    """
    parts = []

    # Title is most important - add it with emphasis
    title_clean = preprocess_text(title)
    if title_clean:
        parts.append(f"Вакансия: {title_clean}")

    # Knowledge/skills are critical for matching
    knowledge_clean = preprocess_text(knowledge)
    if knowledge_clean:
        parts.append(f"Требования и навыки: {knowledge_clean}")

    # City provides location context
    city_clean = preprocess_text(city)
    if city_clean and city_clean.lower() not in ('unknown', 'неизвестно', 'nan', 'none'):
        parts.append(f"Город: {city_clean}")

    # Company can be relevant for matching
    company_clean = preprocess_text(company)
    if company_clean and company_clean.lower() not in ('unknown', 'неизвестно', 'nan', 'none'):
        parts.append(f"Компания: {company_clean}")

    # Additions provide extra context (remote work, experience level, etc.)
    additions_clean = preprocess_text(additions)
    if additions_clean and additions_clean not in ('[]', ''):
        # Clean up list-like formatting
        additions_clean = additions_clean.replace('[', '').replace(']', '').replace("'", "")
        if additions_clean:
            parts.append(f"Условия: {additions_clean}")

    return ". ".join(parts)


def create_query_embedding_text(query: str) -> str:
    """
    Preprocess user search query for better matching.
    """
    query_clean = preprocess_text(query)

    if not query_clean:
        return ""

    # Add context that this is a job search query
    return f"Ищу работу: {query_clean}"


def embed_text(text: str):
    """
    Embed a single text string into a normalized vector.
    """
    if not text or not text.strip():
        return None

    cleaned = preprocess_text(text)
    if not cleaned:
        return None

    return _model.encode(cleaned, normalize_embeddings=True).tolist()


def embed_job(title: str, knowledge: str, city: str = "",
              company: str = "", additions: str = ""):
    """
    Create embedding for a job posting with rich context.
    """
    combined_text = create_job_embedding_text(title, knowledge, city, company, additions)

    if not combined_text:
        return None

    return _model.encode(combined_text, normalize_embeddings=True).tolist()


def embed_query(query: str):
    """
    Create embedding for a user search query with context.
    """
    query_text = create_query_embedding_text(query)

    if not query_text:
        return None

    return _model.encode(query_text, normalize_embeddings=True).tolist()


def embed_texts_batch(texts):
    """
    Batch embed multiple texts (preprocessed).
    """
    cleaned_texts = [preprocess_text(t) for t in texts]
    # Filter out empty texts but track indices
    valid_indices = [i for i, t in enumerate(cleaned_texts) if t]
    valid_texts = [cleaned_texts[i] for i in valid_indices]

    if not valid_texts:
        return [None] * len(texts)

    embeddings = _model.encode(valid_texts, normalize_embeddings=True, show_progress_bar=True).tolist()

    # Reconstruct results with None for empty texts
    results = [None] * len(texts)
    for idx, emb in zip(valid_indices, embeddings):
        results[idx] = emb

    return results