from django.core.management.base import BaseCommand
from NeuralHire.models import Job
from utils.embeddings import embed_job
import time

class Command(BaseCommand):
    help = 'Re-embed all jobs using the current embedding model'

    def handle(self, *args, **kwargs):
        jobs = Job.objects.all()
        total = jobs.count()
        self.stdout.write(f"Found {total} jobs to re-embed...")
        
        count = 0
        for job in jobs:
            try:
                # Re-create embedding
                # embed_job function handles text creation internally based on fields
                embedding = embed_job(
                    title=job.title,
                    knowledge=job.knoladge,
                    city=job.city,
                    company=job.company,
                    additions=job.addition
                )
                
                if embedding:
                    job.content_embedding = embedding
                    job.save()
                    count += 1
                    
                if count % 100 == 0:
                    self.stdout.write(f"Processed {count}/{total} jobs...")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing job {job.id}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"Successfully re-embedded {count} jobs."))
