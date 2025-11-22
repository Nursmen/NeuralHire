# utils/embeddings.py
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer('all-MiniLM-L6-v2')

def embed_text(text: str):
    if not text or not text.strip():
        return None
    return _model.encode(text.strip(), normalize_embeddings=True).tolist()

def embed_texts_batch(texts):
    return _model.encode(texts, normalize_embeddings=True, show_progress_bar=True).tolist()