# Academia Fast Scraper API

A high-performance FastAPI application for scraping student data from the SRM student portal. Features advanced CAPTCHA solving using OCR and parallel data fetching.

## Features

✨ **Fast & Efficient**
- Parallel data fetching (~0.3s for 9 endpoints)
- Advanced CAPTCHA solving using OpenCV + Tesseract OCR
- Optimized image preprocessing techniques
- Connection pooling for HTTP requests

📊 **Comprehensive Data**
- Student profile & personal details
- Attendance records
- Semester results & grades
- Timetable
- Internal marks
- Hall ticket
- Personal & subject information

🛡️ **Robust**
- Automatic retry mechanism (up to 10 attempts)
- Error handling & detailed logging
- Optional dependencies (graceful degradation)
- CORS enabled for frontend integration

## Prerequisites

### System Requirements
- Python 3.8+
- Ubuntu/Debian-based Linux (for Tesseract)

### System Dependencies
The following must be installed system-wide:
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

### Python Packages
All listed in `requirements.txt`:
- FastAPI
- Uvicorn
- Requests
- BeautifulSoup4
- OpenCV (cv2)
- NumPy
- Pytesseract
- lxml
- And more...

## Installation

### Quick Setup (Automated)
```bash
bash deployment_setup.sh
```

### Manual Setup
1. **Install system dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
   ```

2. **Create virtual environment:**
   ```bash
   python3 -m venv academia_fast_env
   source academia_fast_env/bin/activate
   ```

3. **Install Python packages:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Verify installation:**
   ```bash
   python3 -c "import cv2; import numpy; import pytesseract; print('✅ All dependencies ready')"
   ```

## Running the Application

### Development
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`

## API Endpoints

### 1. Health Check
```bash
GET /health
```
Response:
```json
{"status": "ok"}
```

### 2. Academia Portal Scraper (Original)
```bash
POST /scrape
Content-Type: application/json

{
  "email": "student_email@example.com",
  "password": "student_password"
}
```

### 3. SRM Student Portal Scraper ⭐
```bash
POST /studentportal_result
Content-Type: application/json

{
  "netid": "as0711",
  "password": "your_password"
}
```

**Response (Success):**
```json
{
  "status": "success",
  "student_info": {
    "reg_no": "RA2311056010161",
    "name": "STUDENT NAME",
    "photo_url": "https://..."
  },
  "dashboard_info": [...],
  "personal_details": [...],
  "subjects_offered": [...],
  "attendance_details": [...],
  "semester_results": [...],
  "timetable": [...],
  "internal_marks": [...],
  "hall_ticket": [...],
  "raw_tables": [...],
  "performance": {
    "fetch_time_seconds": 0.33,
    "total_time_seconds": 2.74,
    "parallel_requests": 9
  },
  "saved_to": "output/RA2311056010161_20260120_011811.json"
}
```

**Response (Error - Invalid Credentials):**
```json
{
  "status": "error",
  "message": "Invalid credentials",
  "details": "Could not authenticate with provided credentials."
}
```

## How It Works

### CAPTCHA Solving Pipeline
1. **Fetch CAPTCHA image** from portal
2. **Image preprocessing:**
   - 2x upscaling for better accuracy
   - Multiple threshold variants (adaptive, OTSU, morphological)
3. **OCR with Tesseract:**
   - Multiple PSM (Page Segmentation Modes)
   - Character whitelist filtering
   - Validation (4-8 alphanumeric characters)
4. **Return best result** with highest confidence

### Login Flow
1. Fetch login page to extract CSRF token
2. Solve CAPTCHA (with retry logic)
3. Send login credentials with CAPTCHA
4. Verify authentication (check for "logout" button)
5. If authenticated, proceed to data scraping

### Data Fetching
- Parallel requests to 9 endpoints using ThreadPoolExecutor
- Table parsing with BeautifulSoup
- Data aggregation and JSON export
- Automatic save to `output/` directory

## Performance

**Benchmark Results:**
- CAPTCHA solving: ~0.2-0.5 seconds (with OCR)
- Data fetching: ~0.3 seconds (9 parallel requests)
- Total execution time: ~2-4 seconds

## Troubleshooting

### CAPTCHA Solver Unavailable
**Error:** "CAPTCHA solver unavailable (missing cv2/numpy/pytesseract)"

**Solution:** Missing optional dependencies
```bash
pip install opencv-python numpy pytesseract
```

### Tesseract Not Found
**Error:** Related to Tesseract binary not being found

**Solution:** Install Tesseract system package
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

### Login Failed (10/10 Attempts)
**Possible causes:**
1. Invalid credentials
2. CAPTCHA OCR accuracy issues
3. Portal temporarily unavailable
4. Account locked

**Solution:**
- Verify credentials are correct
- Try again (portal may be temporarily down)
- Check if account is active on the portal

### ImportError: No module named 'lxml'
**Solution:**
```bash
pip install lxml
```

## Docker Deployment

### Dockerfile Example
```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Run the application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build and Run
```bash
docker build -t academia-scraper .
docker run -p 8000:8000 academia-scraper
```

## Development

### Project Structure
```
academia_fast_scrapper/
├── app.py                          # Main FastAPI application
├── requirements.txt                # Python dependencies
├── deployment_setup.sh            # Deployment script
├── Readme.md                       # This file
├── Dockerfile                      # Docker configuration
│
├── tools/
│   ├── studentportal_result.py    # SRM portal scraper logic
│   ├── fallback_mock_attendance_data.py
│   └── studentportal_result.py
│
├── utils/
│   └── parser.py                  # Parsing utilities
│
├── output/                        # Scraped data storage
│   └── *.json                     # JSON files with student data
│
└── academia_fast_env/             # Virtual environment
```

### Adding New Features
1. Create endpoint in `app.py`
2. Add scraping logic in `tools/`
3. Update dependencies in `requirements.txt`
4. Test locally before deployment
5. Update documentation

## Important Notes

⚠️ **Security**
- Never hardcode credentials in code
- Use environment variables for sensitive data
- Validate all user inputs
- Use HTTPS in production

⚠️ **Terms of Service**
- This tool is for educational purposes
- Respect the portal's terms of service
- Do not overload the server with requests
- Implement rate limiting if needed

## License

[Add your license here]

## Support

For issues or questions:
- Check the troubleshooting section above
- Review the error messages and logs
- Verify all dependencies are installed
- Ensure Tesseract binary is available

## Contributors

- Akshat Srivastava (Original Author)

---

**Last Updated:** January 2026
