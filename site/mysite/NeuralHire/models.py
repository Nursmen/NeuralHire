# models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField  # Это встроено в Django, ничего устанавливать не нужно


class Job(models.Model):
    title = models.CharField(max_length=255)

    content_embedding = ArrayField(
        models.FloatField(),      
        size=384,                
        null=True,
        blank=True,
    )

    knoladge = models.TextField(blank=True)
    money = models.IntegerField(null=True, blank=True)
    addition = models.TextField(blank=True)
    city = models.CharField(max_length=255, blank=True)
    link = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True, default='Unknown')

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            # Ускоряет обычные запросы
            models.Index(fields=['city']),
            models.Index(fields=['money']),
        ]