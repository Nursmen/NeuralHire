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


def test_extract_bbox(pdf_path, keyword):
    """
    TEST FUNCTION: Extract bounding box coordinates for a keyword in the resume.
    Uses Qwen VL to locate text and return coordinates.
    
    Args:
        pdf_path: Path to PDF resume
        keyword: Text to locate (e.g., "Python", "опыт работы")
    
    Returns:
        dict with bbox coordinates: {"bbox": [x1, y1, x2, y2], "page": page_num}
    """
    try:
        print(f"\n=== Testing bbox extraction for keyword: '{keyword}' ===")
        
        # Convert PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt='png', last_page=2)
            if not images:
                print("No images generated from PDF")
                return None
            
            # Try each page
            for page_num, image in enumerate(images, 1):
                img_path = os.path.join(temp_dir, f'page_{page_num}.png')
                image.save(img_path, 'PNG')
                
                # Encode to base64
                base64_image = encode_image_to_base64(img_path)
                print(f"Image size: {image.size}")
                
                # Construct grounding prompt
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            },
                            {
                                "type": "text",
                                "text": f"""Locate the word "{keyword}" in this document image.
                                
If you find it, respond with:
{{"found": true, "bbox": [x1, y1, x2, y2]}}

If not found, respond with:
{{"found": false}}

The bbox coordinates should be normalized to 0-1000 range relative to the image dimensions."""
                            }
                        ]
                    }
                ]
                
                print(f"Trying page {page_num}...")
                
                # Call Qwen VL
                completion = client.chat.completions.create(
                    model="qwen-vl-max",  # Using max for better grounding
                    messages=messages
                )
                
                result_text = completion.choices[0].message.content
                print(f"Raw response: {result_text}")
                
                # Parse JSON
                try:
                    if '```json' in result_text:
                        result_text = result_text.split('```json')[1].split('```')[0].strip()
                    elif '```' in result_text:
                        result_text = result_text.split('```')[1].split('```')[0].strip()
                    
                    parsed = json.loads(result_text)
                    
                    if parsed.get('found'):
                        print(f"✓ Found on page {page_num}: {parsed}")
                        return {
                            "bbox": parsed.get('bbox'),
                            "page": page_num,
                            "text": parsed.get('text', keyword)
                        }
                except json.JSONDecodeError as je:
                    print(f"JSON parse error: {je}")
                    continue
            
            print("Keyword not found in any page")
            return None
    
    except Exception as e:
        print(f"Exception in test_extract_bbox: {e}")
        import traceback
        traceback.print_exc()
        return None


def extract_keywords_from_explanation(explanation):
    """
    Extract 1 key skill/keyword from a job explanation.
    Uses Qwen to identify the most important term.
    """
    try:
        prompt = f"""From this job match explanation, identify the specific HARD SKILL, TOOL, TECHNOLOGY, CERTIFICATION, or LOCATION (City) that serves as the strongest evidence for this match.

Rules:
1. **PRIORITY**: If a specific City or Location is mentioned as a key match factor, select it as the keyword.
2. Do NOT select generic job titles (e.g., "Cook", "Manager", "Driver", "Engineer").
3. Do NOT select soft skills (e.g., "Communication", "Leadership") unless no hard skills are present.
4. Select a specific term that is likely to be found verbatim in the resume (e.g., "Moscow", "Python", "HACCP", "AutoCAD").
5. Return ONLY a JSON array with one keyword string.

Explanation: {explanation}"""

        completion = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": "Extract ONE specific hard skill, tool, or location as evidence. Return only JSON array."},
                {"role": "user", "content": prompt}
            ]
        )

        result = completion.choices[0].message.content
        
        # Parse JSON
        if '```json' in result:
            result = result.split('```json')[1].split('```')[0].strip()
        elif '```' in result:
            result = result.split('```')[1].split('```')[0].strip()
        
        keywords = json.loads(result)
        return keywords[:1]  # Only 1 keyword
    
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return []


def extract_resume_crops(pdf_path, keywords_list, output_dir):
    """
    Extract and crop sections of resume for given keywords.
    
    Args:
        pdf_path: Path to resume PDF
        keywords_list: List of keywords to locate
        output_dir: Directory to save cropped images
    
    Returns:
        dict: {keyword: crop_image_path}
    """
    from PIL import Image
    
    crops = {}
    
    try:
        # Convert PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, output_folder=temp_dir, fmt='png', last_page=2)
            if not images:
                return crops
            
            # Save full page images
            page_images = []
            for i, image in enumerate(images, 1):
                img_path = os.path.join(temp_dir, f'page_{i}.png')
                image.save(img_path, 'PNG')
                page_images.append((i, img_path, image))
            
            # For each keyword, find and crop
            for keyword in keywords_list:
                print(f"Looking for: {keyword}")
                
                # Try each page
                for page_num, img_path, pil_image in page_images:
                    base64_image = encode_image_to_base64(img_path)
                    
                    messages = [{
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                            },
                            {
                                "type": "text",
                                "text": f"""Locate the word "{keyword}" in this document image.
                                
                                If you find it, respond with:
                                {{"found": true, "bbox": [x1, y1, x2, y2]}}

                                If not found, respond with:
                                {{"found": false}} 
                                """
                            }
                        ]
                    }]
                    
                    completion = client.chat.completions.create(
                        model="qwen-vl-max",
                        messages=messages
                    )
                    
                    result_text = completion.choices[0].message.content
                    
                    try:
                        if '```json' in result_text:
                            result_text = result_text.split('```json')[1].split('```')[0].strip()
                        elif '```' in result_text:
                            result_text = result_text.split('```')[1].split('```')[0].strip()
                        
                        parsed = json.loads(result_text)
                        
                        if parsed.get('found'):
                            bbox = parsed['bbox']
                            
                            x1, y1, x2, y2 = map(int, bbox)
                            if bbox[2] < bbox[0] or bbox[3] < bbox[1]:
                                x, y, w, h = bbox
                                x1, y1, x2, y2 = x, y, x + w, y + h
                            
                            # Crop image
                            cropped = pil_image.crop((x1, y1, x2, y2))
                            
                            # Save crop
                            os.makedirs(output_dir, exist_ok=True)
                            crop_filename = f"crop_{keyword.replace(' ', '_')}_{page_num}.png"
                            crop_path = os.path.join(output_dir, crop_filename)
                            cropped.save(crop_path, 'PNG')
                            
                            crops[keyword] = crop_path
                            print(f"✓ Cropped '{keyword}' -> {crop_filename}")
                            break  # Found on this page, move to next keyword
                    
                    except json.JSONDecodeError:
                        continue
    
    except Exception as e:
        print(f"Error in extract_resume_crops: {e}")
        import traceback
        traceback.print_exc()
    
    return crops
