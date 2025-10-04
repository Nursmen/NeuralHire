import pandas as pd
from django.core.management.base import BaseCommand
from NeuralHire.models import *

class Command(BaseCommand):
    help = 'Imports job data from jobs.csv into the Job model'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the jobs.csv file')

    def handle(self, *args, **options):
        csv_file = options['csv_file']
        try:
            # Read CSV file
            df = pd.read_csv(csv_file)
            expected_columns = ['title', 'money', 'knoladge', 'company', 'addition', 'city', 'link']
            if not all(col in df.columns for col in expected_columns):
                self.stderr.write("Error: CSV file must contain columns: " + ", ".join(expected_columns))
                return

            # Clear existing data (optional, comment out if you want to append)
            Job.objects.all().delete()
            self.stdout.write("Cleared existing Job records.")

            # Iterate over CSV rows and create Job instances
            for _, row in df.iterrows():
                # Handle missing or invalid data
                title = str(row['title'])[:255] if pd.notna(row['title']) else 'Unknown'
                money = int(row['money']) if pd.notna(row['money']) else 0
                knoladge = str(row['knoladge']) if pd.notna(row['knoladge']) else ''
                company = str(row['company'])[:255] if pd.notna(row['company']) else 'Unknown'
                addition = str(row['addition']) if pd.notna(row['addition']) else ''
                city = str(row['city'])[:255] if pd.notna(row['city']) else 'Unknown'
                link = str(row['link']) if pd.notna(row['link']) else ''

                # Create and save Job instance
                Job.objects.create(
                    title=title,
                    money=money,
                    knoladge=knoladge,
                    addition=addition,
                    city=city,
                    link=link
                )

            self.stdout.write(self.style.SUCCESS(f"Successfully imported {len(df)} jobs from {csv_file}"))

        except FileNotFoundError:
            self.stderr.write(f"Error: File {csv_file} not found")
        except Exception as e:
            self.stderr.write(f"Error during import: {str(e)}")