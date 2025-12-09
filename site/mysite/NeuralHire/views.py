# views.py
from django.shortcuts import render
from django.core.files.storage import default_storage
from NeuralHire.models import Job, Resume
from utils.embeddings import (
    embed_query, rerank_results, compute_keyword_boost,
    create_job_text, create_job_summary, llm_validate_results
)
from utils.qwen_vl import summarize_resume, explain_job_match
import numpy as np

list_of_additions = [
    'Отклик без резюме',
    'Опыт не нужен',
    'Доступно для соискателей от 45+ лет',
    'Удаленная работа',
    'Доступно для соискателей с ограниченными возможностями',
    'Доступно студентам',
]

# Configuration
CANDIDATES_FOR_RERANK = 100
CANDIDATES_FOR_CROSS_ENCODER = 30
FINAL_RESULTS = 20
KEYWORD_BOOST_WEIGHT = 0.5
USE_LLM_VALIDATION = False


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

    query_embedding = embed_query(user_query)
    if query_embedding is None:
        return render(request, 'neuralhire/results.html', {'error': 'Не удалось обработать запрос'})

    query_vec = np.array(query_embedding)
    jobs_data = list(Job.objects.filter(content_embedding__isnull=False)
                     .values('id', 'content_embedding', 'addition', 'title', 'knoladge', 'city', 'company'))

    if not jobs_data:
        return render(request, 'neuralhire/results.html', {'error': 'Нет вакансий с эмбеддингами'})

    job_matrix = np.array([j['content_embedding'] for j in jobs_data])
    embedding_scores = np.dot(job_matrix, query_vec)

    combined_scores = []
    for index, emb_score in enumerate(embedding_scores):
        job_item = jobs_data[index]

        if selected_additions:
            job_additions = job_item['addition'] if job_item['addition'] else ""
            if not any(sel_add in job_additions for sel_add in selected_additions):
                continue

        job_text = create_job_text(
            job_item['title'], job_item['knoladge'],
            job_item.get('city', ''), job_item.get('company', ''),
            job_item.get('addition', '')
        )

        keyword_boost = compute_keyword_boost(user_query, job_text)
        final_score = emb_score + (keyword_boost * KEYWORD_BOOST_WEIGHT)

        combined_scores.append({
            'index': index, 'id': job_item['id'], 'score': final_score,
            'job_text': job_text, 'title': job_item['title'],
            'knoladge': job_item['knoladge'],
            'city': job_item.get('city', ''), 'company': job_item.get('company', '')
        })

    combined_scores.sort(key=lambda x: x['score'], reverse=True)
    candidates = combined_scores[:CANDIDATES_FOR_RERANK]

    if not candidates:
        return render(request, 'neuralhire/results.html', {
            'error': 'Не найдено подходящих вакансий',
            'additions': list_of_additions
        })

    candidate_texts = [c['job_text'] for c in candidates]
    reranked = rerank_results(user_query, candidate_texts, top_k=CANDIDATES_FOR_CROSS_ENCODER)

    reranked_candidates = [candidates[idx] for idx, _ in reranked]
    reranked_scores = [score for _, score in reranked]

    if USE_LLM_VALIDATION and len(reranked_candidates) > 0:
        job_summaries = [create_job_summary(c['title'], c['knoladge'], c['city'], c['company'])
                         for c in reranked_candidates]
        llm_order = llm_validate_results(user_query, job_summaries, top_k=FINAL_RESULTS)
        final_candidates = [reranked_candidates[i] for i in llm_order if i < len(reranked_candidates)]
        final_scores = [reranked_scores[i] for i in llm_order if i < len(reranked_scores)]
    else:
        final_candidates = reranked_candidates[:FINAL_RESULTS]
        final_scores = reranked_scores[:FINAL_RESULTS]

    top_ids = [c['id'] for c in final_candidates]
    jobs_queryset = Job.objects.filter(id__in=top_ids)
    jobs_dict = {job.id: job for job in jobs_queryset}

    final_jobs = []
    scores_list = []

    for i, candidate in enumerate(final_candidates):
        job_obj = jobs_dict.get(candidate['id'])
        if job_obj:
            final_jobs.append(job_obj)
            score = final_scores[i] if i < len(final_scores) else 0.0
            scores_list.append(round(float(score), 4))

    return render(request, 'neuralhire/results.html', {
        'user_query': user_query,
        'jobs': final_jobs,
        'scores': scores_list,
        'zipped_results': zip(final_jobs, scores_list),
        'selected_additions': selected_additions,
        'additions': list_of_additions,
        'comma_delimiter': ',',
    })


def upload_resume(request):
    """Handle PDF resume upload and job matching."""
    if request.method != "POST":
        return render(request, 'neuralhire/index.html', {'additions': list_of_additions})
    
    if 'resume_pdf' not in request.FILES:
        return render(request, 'neuralhire/results.html', {
            'error': 'Пожалуйста, загрузите PDF файл резюме',
            'additions': list_of_additions
        })
    
    pdf_file = request.FILES['resume_pdf']
    
    if not pdf_file.name.endswith('.pdf'):
        return render(request, 'neuralhire/results.html', {
            'error': 'Пожалуйста, загрузите файл в формате PDF',
            'additions': list_of_additions
        })
    
    try:
        file_path = default_storage.save(f'temp/{pdf_file.name}', pdf_file)
        full_path = default_storage.path(file_path)
        
        resume_data = summarize_resume(full_path)
        default_storage.delete(file_path)
        
        if not resume_data:
            return render(request, 'neuralhire/results.html', {
                'error': 'Не удалось обработать резюме. Проверьте формат PDF и попробуйте снова.',
                'additions': list_of_additions
            })
        
        skills = resume_data.get('skills', '')
        experience = resume_data.get('experience', '')
        preferences = resume_data.get('preferences', '')
        full_summary = resume_data.get('full_summary', '')
        
        summary_embedding = embed_query(full_summary)
        
        if summary_embedding is None:
            return render(request, 'neuralhire/results.html', {
                'error': 'Не удалось создать эмбеддинг для резюме',
                'additions': list_of_additions
            })
        
        resume_obj = Resume.objects.create(
            pdf_file=pdf_file,
            skills=skills,
            experience=experience,
            preferences=preferences,
            full_summary=full_summary,
            summary_embedding=summary_embedding
        )
        
        query_vec = np.array(summary_embedding)
        jobs_data = list(Job.objects.filter(content_embedding__isnull=False)
                         .values('id', 'content_embedding', 'title', 'knoladge', 'city', 'company', 'addition'))
        
        if not jobs_data:
            return render(request, 'neuralhire/results.html', {
                'error': 'Нет вакансий с эмбеддингами',
                'additions': list_of_additions
            })
        
        job_matrix = np.array([j['content_embedding'] for j in jobs_data])
        embedding_scores = np.dot(job_matrix, query_vec)
        
        scored_jobs = []
        for index, score in enumerate(embedding_scores):
            job_item = jobs_data[index]
            scored_jobs.append({
                'id': job_item['id'],
                'score': float(score),
                'title': job_item['title'],
                'knoladge': job_item['knoladge'],
                'city': job_item.get('city', ''),
                'company': job_item.get('company', ''),
                'addition': job_item.get('addition', '')
            })
        
        scored_jobs.sort(key=lambda x: x['score'], reverse=True)
        
        # Filter by selected additions
        selected_additions = [add for add in list_of_additions if request.POST.get(add)]
        if selected_additions:
            filtered_jobs = []
            for job in scored_jobs:
                job_additions = job.get('addition', '')
                if job_additions and any(sel_add in job_additions for sel_add in selected_additions):
                    filtered_jobs.append(job)
            scored_jobs = filtered_jobs
        
        top_candidates = scored_jobs[:FINAL_RESULTS]
        top_ids = [c['id'] for c in top_candidates]
        
        jobs_queryset = Job.objects.filter(id__in=top_ids)
        jobs_dict = {job.id: job for job in jobs_queryset}
        
        final_jobs = []
        scores_list = []
        
        for candidate in top_candidates:
            job_obj = jobs_dict.get(candidate['id'])
            if job_obj:
                final_jobs.append(job_obj)
                scores_list.append(round(candidate['score'], 4))
        
        # Generate individual AI explanations for top 3 jobs
        job_explanations = []
        if final_jobs:
            for i, job in enumerate(final_jobs[:3]):
                explanation = explain_job_match(full_summary, job)
                job_explanations.append(explanation)
        
        return render(request, 'neuralhire/results.html', {
            'jobs': final_jobs,
            'scores': scores_list,
            'zipped_results': zip(final_jobs, scores_list),
            'resume_summary': {
                'skills': skills,
                'experience': experience,
                'preferences': preferences,
                'full_summary': full_summary
            },
            'job_explanations': job_explanations,
            'additions': list_of_additions,
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return render(request, 'neuralhire/results.html', {
            'error': f'Произошла ошибка при обработке резюме: {str(e)}',
            'additions': list_of_additions
        })