from django.shortcuts import render
from .models import Job

# Create your views here.
def main(request):
    list_of_additions = ['Опыт не нужен', 'Доступно студентам',
                        'Доступно для соискателей от 45+ лет', 'Доступно для соискателей с ограниченными возможностями',
                        'Удаленная работа', 'Отклик без резюме']
    return render(request, 'neuralhire/index.html', {'additions':list_of_additions})