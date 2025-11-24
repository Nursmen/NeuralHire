# management/commands/import_jobs.py
import pandas as pd
from django.core.management.base import BaseCommand
from NeuralHire.models import Job
from utils.embeddings import embed_job
import re


class Command(BaseCommand):
    help = 'Import jobs from CSV and generate embeddings with rich context'

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
        embedding_failures = 0

        for idx, row in df.iterrows():
            title = str(row.get('title', 'Unknown'))[:255]
            knoladge = str(row.get('knoladge', '') or '')
            company = str(row.get('company', 'Unknown'))[:255]
            city = str(row.get('city', 'Unknown'))[:255]
            addition = str(row.get('addition', ''))
            link = str(row.get('link', ''))

            raw_money = row.get('money')
            if pd.isna(raw_money) or raw_money is None:
                money = None
            else:
                raw = str(raw_money).strip().lower()

                if any(phrase in raw for phrase in ['по договорённости', 'договорная', 'не указана', 'negotiable']):
                    money = -1
                else:
                    clean_raw = raw.replace(' ', '').replace('\xa0', '')

                    match = re.search(r'\d+', clean_raw)

                    if match:
                        val = int(match.group())

                        if val > 2147483647:
                            money = -1
                        else:
                            money = val
                    else:
                        money = -1

            # Use the new embed_job function for richer embeddings
            # Includes title, knowledge, city, company, and additions for better context
            embedding = embed_job(
                title=title,
                knowledge=knoladge,
                city=city,
                company=company,
                additions=addition
            )

            if embedding is None or len(embedding) != 384:
                embedding = None
                embedding_failures += 1

            job = Job(
                title=title,
                knoladge=knoladge,
                company=company,
                money=money,
                addition=addition,
                city=city,
                link=link,
                content_embedding=embedding,
            )
            jobs_to_create.append(job)
            count += 1

            if count % 50 == 0:
                self.stdout.write(f"Processed {count} rows...")

        if jobs_to_create:
            self.stdout.write("Saving to database...")
            Job.objects.bulk_create(jobs_to_create)
            self.stdout.write(self.style.SUCCESS(
                f"Successfully created {len(jobs_to_create)} jobs. "
                f"({embedding_failures} embedding failures)"
            ))
        else:
            self.stdout.write(self.style.WARNING("No jobs found to create."))