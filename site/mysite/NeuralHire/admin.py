from django.contrib import admin
from .models import Job

# Register your models here.
class AuthorAdmin(admin.ModelAdmin):
    pass
admin.site.register(Job, AuthorAdmin)