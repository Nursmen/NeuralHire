from django.shortcuts import render, redirect
from .models import Job
import pandas as pd
import joblib

list_of_additions = ['Опыт не нужен', 'Доступно студентам',
                    'Доступно для соискателей от 45+ лет', 'Доступно для соискателей с ограниченными возможностями',
                    'Удаленная работа', 'Отклик без резюме']

# Create your views here.
def main(request):
    if request.method == "POST":
        sth = '[\''
        for i in list_of_additions:
            try:
                sth+=request.POST[i]
                sth+='\', '
            except:
                pass

        sth = sth[:-2]
        sth += ']'
        
        data = [[request.POST['knoladge'], sth, '']]
        df_col = pd.read_csv('./site/mysite/NeuralHire/model/columns.csv')
        df = pd.get_dummies(pd.DataFrame(data, columns=['knoladge', 'addition', 'city']))
        
        for i in df.columns:
            df_col[sth] = 1
        # here we go
        # ok i got a plan
        # i will make a little csv with only columns
        # then just change some data

        model = joblib.load('./site/mysite/NeuralHire/model/model.sav')
        print(model.predict(df_col))

    return render(request, 'neuralhire/index.html', {'additions':list_of_additions})