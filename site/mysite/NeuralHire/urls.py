from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
]