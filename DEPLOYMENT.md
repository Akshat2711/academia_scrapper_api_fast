# Deployment Guide

This guide provides step-by-step instructions for deploying the Academia Fast Scraper API to various environments.

## Table of Contents
1. [Linux Server Deployment](#linux-server-deployment)
2. [Docker Deployment](#docker-deployment)
3. [Troubleshooting](#troubleshooting)

---

## Linux Server Deployment

### Prerequisites
- Ubuntu 20.04 LTS or similar Debian-based system
- Python 3.8+
- Git (optional)
- sudo access

### Step 1: System Dependencies
```bash
sudo apt-get update
sudo apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    tesseract-ocr \
    tesseract-ocr-eng
```

### Step 2: Clone/Download Project
```bash
cd /opt
sudo git clone https://github.com/Akshat2711/academia_scrapper_api_fast.git academia_scraper
cd academia_scraper
```

### Step 3: Setup Python Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Verify Installation
```bash
python3 << 'EOF'
try:
    import cv2
    import numpy
    import pytesseract
    from tools.studentportal_result import scrape_student_portal
    print("✅ All dependencies installed successfully!")
except Exception as e:
    print(f"❌ Error: {e}")
    exit(1)
EOF
```

### Step 5: Run the Application

**Development Mode:**
```bash
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

**Production Mode with Gunicorn:**
```bash
# Install Gunicorn
pip install gunicorn

# Run with multiple workers
gunicorn app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info
```

### Step 6: Systemd Service (Optional)

Create `/etc/systemd/system/academia-scraper.service`:
```ini
[Unit]
Description=Academia Fast Scraper API
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/opt/academia_scraper
Environment="PATH=/opt/academia_scraper/venv/bin"
ExecStart=/opt/academia_scraper/venv/bin/gunicorn \
    app:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 127.0.0.1:8000 \
    --log-level info

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable academia-scraper
sudo systemctl start academia-scraper
sudo systemctl status academia-scraper
```

### Step 7: Setup Reverse Proxy (Nginx)

Create `/etc/nginx/sites-available/academia-scraper`:
```nginx
upstream academia_api {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://academia_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_request_buffering off;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/academia-scraper /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Step 8: SSL Certificate (Let's Encrypt)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d api.example.com
```

---

## Docker Deployment

### Prerequisites
- Docker 20.10+
- Docker Compose 1.29+

### Quick Start

```bash
# Clone repository
git clone https://github.com/Akshat2711/academia_scrapper_api_fast.git
cd academia_scrapper_api_fast

# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f api
```

### Manual Docker Commands

**Build image:**
```bash
docker build -t academia-scraper:latest .
```

**Run container:**
```bash
docker run -d \
    --name academia-scraper \
    -p 8000:8000 \
    -v $(pwd)/output:/app/output \
    academia-scraper:latest
```

**Check status:**
```bash
docker ps | grep academia-scraper
docker logs academia-scraper
```

### Docker with Nginx Reverse Proxy

Update `docker-compose.yml`:
```yaml
version: '3.8'

services:
  api:
    build: .
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./output:/app/output
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
    restart: unless-stopped
```

---

## Kubernetes Deployment

### Create Kubernetes Manifests

**deployment.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: academia-scraper
spec:
  replicas: 3
  selector:
    matchLabels:
      app: academia-scraper
  template:
    metadata:
      labels:
        app: academia-scraper
    spec:
      containers:
      - name: api
        image: academia-scraper:latest
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

**service.yaml:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: academia-scraper-service
spec:
  selector:
    app: academia-scraper
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

**Deploy:**
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get svc academia-scraper-service
```

---

## Troubleshooting

### Issue: "CAPTCHA solver unavailable"

**Problem:** Missing OpenCV, NumPy, or Pytesseract

**Solution:**
```bash
pip install opencv-python numpy pytesseract
```

### Issue: "tesseract is not installed"

**Problem:** Tesseract binary not found

**Solution:**
```bash
# On Ubuntu/Debian
sudo apt-get install tesseract-ocr tesseract-ocr-eng

# On macOS
brew install tesseract

# On CentOS/RHEL
sudo yum install tesseract
```

### Issue: "Login failed after 10 attempts"

**Possible causes:**
1. Invalid credentials
2. Portal temporarily down
3. Account locked
4. CAPTCHA solver accuracy issues

**Solution:**
- Verify credentials are correct
- Check portal status manually
- Try after some time
- Check logs for CAPTCHA success rate

### Issue: Connection refused on localhost:8000

**Solution:**
```bash
# Check if port is in use
lsof -i :8000

# Use different port
uvicorn app:app --port 8001

# Or kill existing process
fuser -k 8000/tcp
```

### Issue: Out of memory

**Solution:**
```bash
# For Docker, increase memory limit
docker update --memory 1g academia-scraper

# For server, optimize Gunicorn workers
gunicorn app:app --workers 2 --worker-class uvicorn.workers.UvicornWorker
```

### Issue: High CPU usage

**Solution:**
```bash
# Reduce worker count
gunicorn app:app --workers 2

# For Docker, limit CPU
docker run --cpus="2" academia-scraper:latest
```

---

## Monitoring and Logging

### Check Application Logs

**With Systemd:**
```bash
sudo journalctl -u academia-scraper -f
```

**With Docker:**
```bash
docker logs -f academia-scraper
```

### Monitor Performance

**Top endpoints by response time:**
```bash
# Check in application logs for "⚡ Total time:"
```

**Check CAPTCHA success rate:**
```bash
# Look for "CAPTCHA:" entries in logs
```

### Set Up Log Aggregation

**ELK Stack (Elasticsearch, Logstash, Kibana):**
```bash
# Configure your logging framework to send to ELK
# See logging configuration in app.py
```

---

## Backup and Recovery

### Backup Data

```bash
# Backup scraped student data
tar -czf backup_output_$(date +%Y%m%d).tar.gz output/

# Upload to cloud storage
aws s3 cp backup_output_*.tar.gz s3://your-bucket/backups/
```

### Recovery

```bash
# Restore from backup
tar -xzf backup_output_20260120.tar.gz

# Verify data integrity
ls -la output/
```

---

## Performance Tuning

### Uvicorn Workers
```bash
# Calculate optimal workers: (2 × CPU cores) + 1
# For 4 cores: 9 workers
uvicorn app:app --workers 9
```

### Connection Pooling
Already optimized in the code:
- HTTP connection pool: 20 connections
- Max retries: 3 with backoff

### Database Optimization (if using)
- Enable query caching
- Index frequently searched fields
- Use connection pooling

---

## Security Hardening

1. **Use HTTPS/TLS:**
   ```bash
   # Let's Encrypt with Certbot
   sudo certbot certonly --standalone -d api.example.com
   ```

2. **Rate Limiting:**
   ```python
   from slowapi import Limiter
   limiter = Limiter(key_func=get_remote_address)
   
   @app.post("/studentportal_result")
   @limiter.limit("5/minute")
   async def scrape_portal(request):
       pass
   ```

3. **Input Validation:**
   - Already implemented with Pydantic BaseModel

4. **Environment Variables:**
   ```bash
   export SRM_API_KEY="your-secret-key"
   ```

---

## Scaling

### Horizontal Scaling
- Run multiple instances behind a load balancer
- Each instance can handle ~10-20 concurrent requests

### Vertical Scaling
- Increase server resources (CPU, RAM)
- Optimize code and dependencies

### Caching
- Implement Redis caching for frequently accessed data
- Cache CAPTCHA solving results (with appropriate TTL)

---

**Last Updated:** January 2026
