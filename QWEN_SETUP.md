# NeuralHire - Qwen VL Integration Setup

## Required Dependencies

Install the following Python packages:

```bash
pip install openai pdf2image
```

**Note**: We use the OpenAI SDK with Qwen's OpenAI-compatible API endpoint.

## System Dependencies

### Windows
You need to install Poppler for Windows:

1. Download poppler from: https://github.com/oschwartz10612/poppler-windows/releases/
2. Extract the archive
3. Add the `bin` folder to your system PATH

Alternatively, you can install via conda:
```bash
conda install -c conda-forge poppler
```

## API Key Configuration

The application automatically loads the API key from `env.env` file in the project root.

1. Create `env.env` file (or copy from `env.env.example`):
```bash
# env.env
DASHSCOPE_API_KEY=your-dashscope-api-key-here
```

2. Add your actual Dashscope API key to this file

**Note**: The `env.env` file is gitignored for security. Never commit your API keys!

## Database Migration

Run migrations to create the Resume model:

```bash
cd site/mysite
python manage.py makemigrations
python manage.py migrate
```

## Testing

1. Start the development server:
```bash
python manage.py runserver
```

2. Navigate to http://localhost:8000
3. Try uploading a PDF resume
4. Verify that:
   - Resume is analyzed by Qwen VL
   - Skills, experience, and preferences are extracted
   - Matching jobs are found
   - AI explanation is generated

## Notes

- Uses **OpenAI SDK** with Qwen's OpenAI-compatible API
- Uses **Qwen-VL-Plus** model for vision analysis
- Uses **Qwen-Plus** for text generation (explanations)
- API endpoint: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`
- The Qwen API requires a Dashscope account (Singapore region)
- PDF processing may take 10-30 seconds depending on file size
- First 2 pages of the resume are analyzed
- Images are base64-encoded for API transmission
- Vector search uses the existing embedding infrastructure
- API key is loaded from `env.env` file automatically
