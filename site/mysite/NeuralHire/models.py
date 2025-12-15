# models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField

class Job(models.Model):
    title = models.CharField(max_length=255)

    content_embedding = ArrayField(
        models.FloatField(),      
        size=768,                
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
            models.Index(fields=['city']),
            models.Index(fields=['money']),
        ]


class Resume(models.Model):
    """Model for storing uploaded resume PDFs and their AI-extracted information."""
    pdf_file = models.FileField(upload_to='resumes/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    # Extracted information from Qwen VL
    skills = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    preferences = models.TextField(blank=True)
    full_summary = models.TextField(blank=True)
    
    # For vector search
    summary_embedding = ArrayField(
        models.FloatField(),
        size=768,
        null=True,
        blank=True,
    )
    
    # Store crop image paths: {job_id: {keyword: crop_path}}
    crop_data = models.JSONField(null=True, blank=True)
    
    def __str__(self):
        return f"Resume uploaded at {self.uploaded_at}"
    
    class Meta:
        ordering = ['-uploaded_at']