# management/commands/import_jobs.py
import pandas as pd
from django.core.management.base import BaseCommand
from NeuralHire.models import Job
from utils.embeddings import embed_text
import re

class Command(BaseCommand):
    help = 'Import jobs from CSV and generate free local embeddings'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        
        try:
            df = pd.read_csv(csv_file)
            self.stdout.write(self.style.SUCCESS(f"CSV loaded. Found {len(df)} rows."))
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("File not found."))
            return

        self.stdout.write("Deleting old jobs...")
        Job.objects.all().delete()

        jobs_to_create = []

        count = 0
        
        for idx, row in df.iterrows():
            title = str(row.get('title', 'Unknown'))[:255]
            knoladge = str(row.get('knoladge', '') or '')
            company = str(row.get('company', 'Unknown'))[:255]

            raw_money = row.get('money')
            if pd.isna(raw_money) or raw_money is None:
                money = None
            else:
                raw = str(raw_money).strip().lower()
                
                if any(phrase in raw for phrase in ['по договорённости', 'договорная', 'не указана', 'negotiable']):
                    money = -1
                else:
                    clean_raw = raw.replace(' ', '').replace('\xa0', '') # handles non-breaking spaces too

                    match = re.search(r'\d+', clean_raw)
                    
                    if match:
                        val = int(match.group())
                        
                        if val > 2147483647:
                            money = -1 
                        else:
                            money = val
                    else:
                        money = -1

            combined_text = f"{title}. {knoladge}".strip()
            embedding = embed_text(combined_text)
            if embedding is None or len(embedding) != 384:
                embedding = None

            job = Job(
                title=title,
                knoladge=knoladge,
                company=company,
                money=money,
                addition=str(row.get('addition', '')),
                city=str(row.get('city', 'Unknown'))[:255],
                link=str(row.get('link', '')),
                content_embedding=embedding,
            )
            jobs_to_create.append(job)
            count += 1
            
            if count % 50 == 0:
                self.stdout.write(f"Processed {count} rows...")

        if jobs_to_create:
            self.stdout.write("Saving to database...")
            Job.objects.bulk_create(jobs_to_create)
            self.stdout.write(self.style.SUCCESS(f"Successfully created {len(jobs_to_create)} jobs."))
        else:
            self.stdout.write(self.style.WARNING("No jobs found to create."))