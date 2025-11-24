# from django.shortcuts import render, redirect
# from .models import Job
# import pandas as pd
# import joblib
# import numpy as np

# list_of_additions = ['Отклик без резюме', 'Опыт не нужен',
#                     'Доступно для соискателей от 45+ лет',
#                     'Удаленная работа', 'Доступно для соискателей с ограниченными возможностями', 'Доступно студентам']

# # Create your views here.
# def main(request):
#     if request.method == "POST":
#         addition = '[\''
#         for i in list_of_additions:
#             try:
#                 addition+=request.POST[i]
#                 addition+='\', \''
#             except:
#                 pass

#         addition = addition[:-3]
#         addition += ']'
        
#         df_col = pd.read_csv('./site/mysite/NeuralHire/model/columns.csv')
#         df_col = df_col.drop(['Unnamed: 0', 'money'], axis=1)

#         for i in request.POST['knoladge'].upper().split(' '):
#             if i in df_col.columns:
#                 df_col[i] = 1
        
#         if addition != '':
#             addition = 'addition_'+addition

#         if addition in df_col.columns:
#             df_col[addition] = 1

#         # here we go
#         # ok i got a plan
#         # i will make a little csv with only columns
#         # then just change some data

#         model = joblib.load('./site/mysite/NeuralHire/model/model.sav')
#         prediciton = np.round(model.predict(df_col), 2)

#         # now we need to find jobs

#         std = 10

#         # instead of > and < u need to use gte (greater or equal) and lte (lower or equal)
#         results = Job.objects.filter(money__lte = (int(prediciton[0])+std), money__gte = (int(prediciton[0])-std))[:3]
#         for i in results:
#             print(i.link)

#         return render(request, 'neuralhire/results.html', {'prediction':int(prediciton[0] * 1000), 
#                                                             'jobs': results})

#     return render(request, 'neuralhire/index.html', {'additions':list_of_additions})


# views.py
from django.shortcuts import render
from NeuralHire.models import Job
from utils.embeddings import embed_query, rerank_results, compute_keyword_boost, create_job_text
import numpy as np

list_of_additions = [
    'Отклик без резюме',
    'Опыт не нужен',
    'Доступно для соискателей от 45+ лет',
    'Удаленная работа',
    'Доступно для соискателей с ограниченными возможностями',
    'Доступно студентам',
]

# How many candidates to retrieve before reranking
CANDIDATES_FOR_RERANK = 50
# Final number of results to show
FINAL_RESULTS = 20
# Weight for keyword boost (0.0-1.0)
KEYWORD_BOOST_WEIGHT = 0.3


def main(request):
    if request.method != "POST":
        return render(request, 'neuralhire/index.html', {'additions': list_of_additions})

    user_query = request.POST.get('knoladge', '').strip()

    selected_additions = [add for add in list_of_additions if request.POST.get(add)]

    if not user_query:
        return render(request, 'neuralhire/results.html', {
            'error': 'Введите описание вакансии или навыки',
            'additions': list_of_additions
        })

    # Use specialized query embedding
    query_embedding = embed_query(user_query)

    if query_embedding is None:
        return render(request, 'neuralhire/results.html', {'error': 'Не удалось обработать запрос'})

    query_vec = np.array(query_embedding)

    # Get all jobs with embeddings, including title and knoladge for reranking
    jobs_data = list(Job.objects.filter(content_embedding__isnull=False)
                     .values('id', 'content_embedding', 'addition', 'title', 'knoladge', 'city', 'company'))

    if not jobs_data:
        return render(request, 'neuralhire/results.html', {'error': 'Нет вакансий с эмбеддингами'})

    job_matrix = np.array([j['content_embedding'] for j in jobs_data])

    # Stage 1: Fast vector similarity search
    embedding_scores = np.dot(job_matrix, query_vec)

    # Stage 2: Add keyword boost to embedding scores
    combined_scores = []
    for index, emb_score in enumerate(embedding_scores):
        job_item = jobs_data[index]

        # Filter by selected additions first
        if selected_additions:
            job_additions = job_item['addition'] if job_item['addition'] else ""
            if not any(sel_add in job_additions for sel_add in selected_additions):
                continue

        # Create job text for keyword matching
        job_text = create_job_text(
            job_item['title'],
            job_item['knoladge'],
            job_item.get('city', ''),
            job_item.get('company', ''),
            job_item.get('addition', '')
        )

        # Compute keyword boost
        keyword_boost = compute_keyword_boost(user_query, job_text)

        # Combine scores: embedding + keyword boost
        final_score = emb_score + (keyword_boost * KEYWORD_BOOST_WEIGHT)

        combined_scores.append({
            'index': index,
            'id': job_item['id'],
            'score': final_score,
            'job_text': job_text
        })

    # Sort by combined score
    combined_scores.sort(key=lambda x: x['score'], reverse=True)

    # Take top candidates for reranking
    candidates = combined_scores[:CANDIDATES_FOR_RERANK]

    if not candidates:
        return render(request, 'neuralhire/results.html', {
            'error': 'Не найдено подходящих вакансий',
            'additions': list_of_additions
        })

    # Stage 3: Rerank using cross-encoder (FREE, local model)
    candidate_texts = [c['job_text'] for c in candidates]
    reranked = rerank_results(user_query, candidate_texts, top_k=FINAL_RESULTS)

    # Build final results
    top_ids = [candidates[idx]['id'] for idx, _ in reranked]

    jobs_queryset = Job.objects.filter(id__in=top_ids)
    jobs_dict = {job.id: job for job in jobs_queryset}

    final_jobs = []
    scores_list = []

    for idx, rerank_score in reranked:
        job_id = candidates[idx]['id']
        job_obj = jobs_dict.get(job_id)
        if job_obj:
            final_jobs.append(job_obj)
            scores_list.append(round(float(rerank_score), 4))

    return render(request, 'neuralhire/results.html', {
        'user_query': user_query,
        'jobs': final_jobs,
        'scores': scores_list,
        'zipped_results': zip(final_jobs, scores_list),
        'selected_additions': selected_additions,
        'additions': list_of_additions,
        'comma_delimiter': ',',
    })