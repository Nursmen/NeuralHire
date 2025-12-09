# Quick Poppler Installation Guide for Windows

## Error
You're seeing: `PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?`

## Solution: Install Poppler via Conda (Easiest Method)

If you have conda/anaconda installed, this is the fastest way:

```bash
conda install -c conda-forge poppler
```

## Alternative: Manual Installation

If you don't have conda, follow these steps:

### 1. Download Poppler
- Go to: https://github.com/oschwartz10612/poppler-windows/releases/
- Download the latest `Release-XX.XX.X-X.zip` file

### 2. Extract the Archive
- Extract to a permanent location, e.g., `C:\Program Files\poppler`

### 3. Add to PATH

**Option A: Via PowerShell (Current Session Only)**
```powershell
$env:PATH += ";C:\Program Files\poppler\Library\bin"
```

**Option B: Permanent (Recommended)**
1. Press `Win + X` and select "System"
2. Click "Advanced system settings"
3. Click "Environment Variables"
4. Under "System variables", find and select "Path"
5. Click "Edit"
6. Click "New"
7. Add: `C:\Program Files\poppler\Library\bin` (adjust path if you extracted elsewhere)
8. Click "OK" on all dialogs
9. **Restart your terminal/IDE**

### 4. Verify Installation

Open a new terminal and run:
```bash
pdfinfo -v
```

You should see version information if installed correctly.

### 5. Restart Django Server

After installing Poppler:
1. Stop the current server (Ctrl+C)
2. Start it again: `python manage.py runserver`
3. Try uploading a PDF again

## Quick Test

After installation, you can test if it works:

```python
from pdf2image import convert_from_path
# Should not raise an error if poppler is found
```
