from django.db import models

class Person(models.Model):
    title = models.CharField(max_length=255)
    money = models.IntegerField(blank=True)
    knoladge = models.TextField()
    addition = models.TextField()
    city = models.CharField(max_length=255)
    link = models.TextField()