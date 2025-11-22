# management/commands/import_jobs.py
import pandas as pd
from django.core.management.base import BaseCommand
from NeuralHire.models import Job
from utils.embeddings import embed_text

class Command(BaseCommand):
    def handle(self, *args, **options):
        print(Job.objects.all().count())

        for i in Job.objects.all():
            print(i, i.money)