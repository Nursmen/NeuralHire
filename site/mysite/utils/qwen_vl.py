import os
from openai import OpenAI
import tempfile
from pdf2image import convert_from_path
from pathlib import Path
import base64
import json

# Load environment variables from env.env file in project root
env_file = Path(__file__).resolve().parent.parent.parent.parent / 'env.env'

print(f"Looking for env.env at: {env_file}")
print(f"File exists: {env_file.exists()}")

if env_file.exists():
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
                print(f"Loaded env variable: {key.strip()}")

# Initialize OpenAI client for Qwen
api_key = os.getenv("DASHSCOPE_API_KEY")
print(f"API Key loaded: {'Yes' if api_key else 'No'}")

if not api_key:
    print("WARNING: DASHSCOPE_API_KEY not found in environment!")

client = OpenAI(
    api_key=api_key,
    base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
)


def encode_image_to_base64(image_path):
    """Encode image to base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')


def summarize_resume(pdf_path):
    """
    Extracts summary from a PDF resume using Qwen-VL-Plus via OpenAI-compatible API.
    Returns a dictionary with 'skills', 'experience', 'preferences', and 'full_summary'.
    """
    try:
        # Convert first 2 pages of PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt='png', last_page=2)
            if not images:
                print("No images generated from PDF")
                return None
            
            # Save images and encode to base64
            image_contents = []
            for i, image in enumerate(images):
                img_path = os.path.join(temp_dir, f'page_{i+1}.png')
                image.save(img_path, 'PNG')
                
                # Encode image to base64
                base64_image = encode_image_to_base64(img_path)
                image_contents.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                })
            
            # Construct message with images and text prompt
            content = image_contents + [{
                "type": "text",
                "text": "Проанализируй это резюме. Извлеки ключевые навыки, опыт работы и предпочтения по работе. Составь краткое описание (summary) для поиска вакансий. Верни ответ в формате JSON: {\"skills\": \"...\", \"experience\": \"...\", \"preferences\": \"...\", \"full_summary\": \"...\"}"
            }]
            
            messages = [
                {
                    "role": "user",
                    "content": content
                }
            ]

            # Call Qwen VL Plus via OpenAI-compatible API
            completion = client.chat.completions.create(
                model="qwen-vl-plus",
                messages=messages
            )

            result_text = completion.choices[0].message.content
            
            # Try to parse JSON from response
            try:
                # Sometimes the model wraps JSON in markdown code blocks
                if '```json' in result_text:
                    result_text = result_text.split('```json')[1].split('```')[0].strip()
                elif '```' in result_text:
                    result_text = result_text.split('```')[1].split('```')[0].strip()
                
                parsed = json.loads(result_text)
                return parsed
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw text
                print(f"Could not parse JSON, returning raw text: {result_text}")
                return {
                    'skills': '',
                    'experience': '',
                    'preferences': '',
                    'full_summary': result_text
                }

    except Exception as e:
        print(f"Exception in summarize_resume: {e}")
        import traceback
        traceback.print_exc()
        return None


def summarize_results(resume_summary, jobs):
    """
    Generates a natural language explanation of why these jobs fit the resume.
    Uses Qwen-Plus text model via OpenAI-compatible API.
    """
    try:
        jobs_text = ""
        for i, job in enumerate(jobs):
            jobs_text += f"{i+1}. {job.title} в {job.company} ({job.city})\n"

        prompt = f"""Резюме кандидата: {resume_summary}

Найденные вакансии:
{jobs_text}

Объясни кратко, почему эти вакансии подходят кандидату. Выдели ключевые совпадения."""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "Ты помощник по подбору вакансий. Отвечай кратко и по делу на русском языке."},
                {"role": "user", "content": prompt}
            ]
        )

        return completion.choices[0].message.content

    except Exception as e:
        print(f"Exception in summarize_results: {e}")
        import traceback
        traceback.print_exc()
        return None


def explain_job_match(resume_summary, job):
    """
    Generates explanation for why a single job matches the resume.
    Used for individual job cards.
    """
    try:
        prompt = f"""Резюме кандидата: {resume_summary}

Вакансия: {job.title} в {job.company} ({job.city})
Требования: {job.knoladge[:200]}...

Объясни в 2-3 предложениях, почему эта вакансия подходит кандидату."""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "Ты помощник по подбору вакансий. Отвечай очень кратко, 2-3 предложения."},
                {"role": "user", "content": prompt}
            ]
        )

        return completion.choices[0].message.content

    except Exception as e:
        print(f"Exception in explain_job_match: {e}")
        return None
