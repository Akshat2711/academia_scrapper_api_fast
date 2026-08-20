# Academia Fast Scraper API

A high-performance FastAPI application for scraping student data from the SRM student portal. Features advanced OCR-based CAPTCHA handling, session reuse, retry-driven page parsing, and fast endpoint fetches.

## Features

✨ **Fast & Efficient**
- Session reuse and lightweight validation for repeated requests
- Retry-based data fetching on parse failures
- Optimized CAPTCHA solving using OpenCV + Tesseract OCR
- Connection pooling and parallel scraping for speed

📊 **Comprehensive Data**
- Student profile and personal details
- Attendance records
- Semester results and grades
- Timetable
- Internal marks
- Hall ticket
- Personal and subject information

🛡️ **Robust**
- Automatic retry mechanism for failed page parsing
- Session fallback when old session data expires
- Attendance fallback generation from timetable
- Detailed error handling and diagnostics
- CORS enabled for frontend integration

## Architecture

The project is organized as a lightweight FastAPI service with two scraper flows:

```text
Client
  |
  v
FastAPI application (app.py)
  |-- /scrape ----------------------> AcademiaClient (studentinfo_scrap.py)
  |                                    |-- session reuse and validation
  |                                    |-- login and CSRF handling
  |                                    |-- attendance/timetable requests
  |                                    `-- HTML parsing (utils/parser.py)
  |
  |-- /studentportal_result --------> SRM portal scraper (tools/studentportal_result.py)
  |                                    |-- CAPTCHA download and OCR
  |                                    |-- login retry flow
  |                                    |-- 9 parallel data requests
  |                                    `-- table parsing with BeautifulSoup
  |
  `-- /logout ----------------------> Academia session invalidation
```

### Current Data Flow

- `app.py` validates API requests and coordinates authentication, scraping, fallbacks, and responses.
- `/scrape` first attempts to reuse the supplied session. Invalid or expired sessions are cleared and replaced with a fresh login.
- `tools/retry_fetch_failed_login.py` retries failed Academia page parsing with full re-authentication when necessary.
- If attendance parsing fails but timetable data is available, `tools/fallback_mock_attendance_data.py` derives a fallback attendance response.
- `tools/studentportal_result.py` uses OpenCV, NumPy, and Tesseract to solve CAPTCHA images, then fetches the student portal's nine data endpoints concurrently through a pooled `requests.Session`.
- `utils/parser.py` converts Academia's embedded HTML responses into structured attendance, marks, timetable, and student data.

### Runtime Layout

```text
app.py                                  API routes and orchestration
studentinfo_scrap.py                   Academia client and session handling
tools/studentportal_result.py          SRM portal login, OCR, and parallel scraping
tools/retry_fetch_failed_login.py      Academia retry and re-authentication flow
tools/fallback_mock_attendance_data.py Timetable-based attendance fallback
utils/parser.py                        Academia HTML parsers
Dockerfile                             Python 3.11 + Tesseract container runtime
```

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
Install required packages from `requirements.txt`. The project uses `opencv-python-headless` for OCR preprocessing in container-friendly environments.

## Installation

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

The API will be available at `http://localhost:8000` for the development command. The Docker image listens on port `8080`.

## API Endpoints

### 1. Health Check
```bash
GET /health
```
Response:
```json
{"status": "ok"}
```

### 2. Academia Portal Scraper
```bash
POST /scrape
Content-Type: application/json

{
  "email": "student_email@example.com",
  "password": "student_password"
}
```

Optional session reuse:
```json
{
  "email": "student_email@example.com",
  "password": "student_password",
  "session_data": { ... }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "attendance": { ... },
  "timetable": { ... },
  "session_data": { ... },
  "session_info": {
    "session_reused": false,
    "session_type": "new"
  }
}
```

### 3. SRM Student Portal Scraper
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
  }
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

### 4. Logout Endpoint
```bash
POST /logout
Content-Type: application/json

{
  "email": "student_email@example.com",
  "password": "student_password",
  "session_data": { ... }
}
```

**Response (Success):**
```json
{
  "status": "success",
  "message": "Logged out successfully"
}
```

## How It Works

### Session Reuse and Fallback
- `/scrape` can reuse an existing `session_data` payload
- If the reused session is invalid, the app falls back to fresh login
- Session validation uses a lightweight attendance request before full scrape

### Retry Fetch Logic
- `tools/retry_fetch_failed_login.py` retries failed page parsing up to 2 times
- On retry, the client may re-authenticate fully and refresh the session
- If timetable parsing fails, attendance is generated from timetable data as a fallback

### CAPTCHA Solving Pipeline
1. Fetch CAPTCHA image from SRM portal
2. Preprocess image for OCR
3. Run Tesseract with multiple configurations
4. Validate 4-8 alphanumeric characters
5. Return the best valid CAPTCHA text

### Data Fetching
- Parallel requests for target endpoints
- Fast HTML table parsing with BeautifulSoup
- Session-aware scraping and retry recovery

## Performance

**Benchmark Results:**
- CAPTCHA solving: ~0.2-0.5 seconds
- Data fetching: ~0.3 seconds for parallel requests
- Full workflow: ~2-4 seconds depending on portal response

## Troubleshooting

### CAPTCHA Solver Unavailable
**Error:** "CAPTCHA solver unavailable (missing cv2/numpy/pytesseract)"

**Solution:**
```bash
pip install opencv-python-headless numpy pytesseract
```

### Tesseract Not Found
**Solution:**
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

## Contributing

Academia Fast Scraper is open source, and fixes, documentation improvements, tests, and performance work are welcome.

1. Fork the repository and create a focused branch from `master`.
2. Use the branch naming format `akshat/<type>/<short-description>`.
  - Fixes: `akshat/fix/what-fixed`
  - Features: `akshat/feat/what-added`
  - Documentation: `akshat/docs/what-changed`
3. Keep changes focused and do not commit credentials, session cookies, CAPTCHA images, or scraped personal data.
4. Run the available checks locally and update the README when behavior or API contracts change.
5. Push the branch and open a pull request against `master`. Explain the problem, the change, and how it was verified.

For a bug report, feature request, or help with development, contact the developer at [akshatsrivastava206@gmail.com](mailto:akshatsrivastava206@gmail.com).

### Login / Session Failure
**Possible causes:**
- Invalid credentials
- Expired or invalid session data
- Portal temporarily unavailable
- Parsing failure on retrieved HTML

### Parse Failures
- The retry mechanism attempts to recover from HTML parse issues
- If attendance parsing fails, mock attendance may be built from timetable data

## Docker Deployment

### Dockerfile Example
```dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

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
├── Readme.md                       # This file
├── Dockerfile                      # Docker configuration
│
├── tools/
│   ├── studentportal_result.py      # SRM portal scraper logic
│   ├── fallback_mock_attendance_data.py
│   ├── retry_fetch_failed_login.py  # Retry and recovery logic
│   └── handle_login_error_codes.py
│
├── utils/
│   └── parser.py                    # Parsing utilities
│
└── academia_fast_env/               # Virtual environment
```

### Adding New Features
1. Create a new endpoint in `app.py`
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
- Use this tool only for permitted educational and self-service scenarios
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
- Ensure the Tesseract binary is available

## Contributors

- Akshat Srivastava (Original Author)

---

**Last Updated:** May 2026
