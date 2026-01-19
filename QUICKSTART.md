# Quick Start Guide

## 🚀 Get Running in 5 Minutes

### Option 1: Docker (Recommended) ⭐

```bash
# Clone repository
git clone https://github.com/Akshat2711/academia_scrapper_api_fast.git
cd academia_scrapper_api_fast

# Start with Docker Compose
docker-compose up -d

# Test the API
curl http://localhost:8000/health
```

✅ **Done!** API is running on `http://localhost:8000`

---

### Option 2: Linux Server (Ubuntu/Debian)

```bash
# Automated setup
bash deployment_setup.sh

# Run the application
source academia_fast_env/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

✅ **Done!** API is running on `http://localhost:8000`

---

### Option 3: Manual Setup

```bash
# 1. Install system dependencies
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install Python packages
pip install -r requirements.txt

# 4. Run the server
uvicorn app:app --host 0.0.0.0 --port 8000
```

✅ **Done!** API is running on `http://localhost:8000`

---

## 📝 Usage Examples

### Health Check
```bash
curl http://localhost:8000/health
```

### Scrape SRM Portal
```bash
curl -X POST http://localhost:8000/studentportal_result \
  -H "Content-Type: application/json" \
  -d '{
    "netid": "as0711",
    "password": "your_password"
  }' | jq .
```

### Response (Success)
```json
{
  "status": "success",
  "student_info": {
    "reg_no": "RA2311056010161",
    "name": "STUDENT NAME",
    "photo_url": "https://..."
  },
  "attendance_details": [...],
  "semester_results": [...],
  "timetable": [...],
  "performance": {
    "fetch_time_seconds": 0.33,
    "total_time_seconds": 2.74,
    "parallel_requests": 9
  }
}
```

---

## 🐛 Troubleshooting

### CAPTCHA Solver Not Working
```bash
# Install missing dependencies
pip install opencv-python numpy pytesseract

# Install Tesseract binary
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

### Port Already in Use
```bash
# Use different port
uvicorn app:app --port 8001

# Or kill existing process
fuser -k 8000/tcp
```

### Login Failed
- ✓ Verify credentials are correct
- ✓ Try again (portal may be temporarily down)
- ✓ Check logs for CAPTCHA errors

---

## 📚 Documentation

- **Full README:** `Readme.md`
- **Deployment Guide:** `DEPLOYMENT.md`
- **Issue Resolution:** `DEPLOYMENT_RESOLUTION.md`

---

## 🔗 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/scrape` | Academia portal scraper |
| `POST` | `/studentportal_result` | ⭐ SRM student portal scraper |

---

## ⚡ Performance

- **CAPTCHA Solving:** ~0.2-0.5s
- **Data Fetching:** ~0.3s (9 parallel requests)
- **Total Time:** ~2-4s per request

---

## ✅ Verification

Check that everything is working:

```bash
# 1. Health check
curl http://localhost:8000/health

# 2. Check dependencies (Docker)
docker exec $(docker-compose ps -q api) python3 -c \
  "import cv2; import numpy; import pytesseract; print('✅ All OK')"

# 3. Check logs
docker-compose logs api | head -20
```

---

## 🆘 Need Help?

1. Check **Readme.md** for API documentation
2. Check **DEPLOYMENT.md** for deployment issues
3. Check **DEPLOYMENT_RESOLUTION.md** for fixed issues
4. Review logs: `docker-compose logs -f api`

---

**Ready to deploy?** Choose your deployment method above and get started! 🚀
