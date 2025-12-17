import os
import django
import sys
import numpy as np

# Setup Django environment
sys.path.append('site/mysite')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
django.setup()

from NeuralHire.models import Job

def check_embeddings():
    job = Job.objects.filter(content_embedding__isnull=False).first()
    if not job:
        print("No jobs found with embeddings.")
        return

    emb_len = len(job.content_embedding)
    print(f"Found job '{job.title}'. Embedding dimension: {emb_len}")
    
    if emb_len == 384:
        print("ALERT: Embeddings are OLD (384 dim). You MUST run reembed_jobs.")
    elif emb_len == 768:
        print("SUCCESS: Embeddings are NEW (768 dim).")
    else:
        print(f"Unknown dimension: {emb_len}")

if __name__ == "__main__":
    check_embeddings()
