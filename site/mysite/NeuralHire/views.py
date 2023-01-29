from django.shortcuts import render, redirect
from .models import Job
import pandas as pd
import joblib
import numpy as np

list_of_additions = ['Отклик без резюме', 'Опыт не нужен',
                    'Доступно для соискателей от 45+ лет',
                    'Удаленная работа', 'Доступно для соискателей с ограниченными возможностями', 'Доступно студентам']

# Create your views here.
def main(request):
    if request.method == "POST":
        addition = '[\''
        for i in list_of_additions:
            try:
                addition+=request.POST[i]
                addition+='\', \''
            except:
                pass

        addition = addition[:-3]
        addition += ']'
        
        df_col = pd.read_csv('./site/mysite/NeuralHire/model/columns.csv')
        df_col = df_col.drop(['Unnamed: 0', 'money'], axis=1)

        for i in request.POST['knoladge'].upper().split(' '):
            if i in df_col.columns:
                df_col[i] = 1
        
        if addition != '':
            addition = 'addition_'+addition

        if addition in df_col.columns:
            df_col[addition] = 1

        # here we go
        # ok i got a plan
        # i will make a little csv with only columns
        # then just change some data

        model = joblib.load('./site/mysite/NeuralHire/model/model.sav')
        prediciton = np.round(model.predict(df_col), 2)

        # now we need to find jobs

        std = 10

        # instead of > and < u need to use gte (greater or equal) and lte (lower or equal)
        results = Job.objects.filter(money__lte = (int(prediciton[0])+std), money__gte = (int(prediciton[0])-std))[:3]
        for i in results:
            print(i.link)

        return render(request, 'neuralhire/results.html', {'prediction':int(prediciton[0] * 1000), 
                                                            'jobs': results})

    return render(request, 'neuralhire/index.html', {'additions':list_of_additions})