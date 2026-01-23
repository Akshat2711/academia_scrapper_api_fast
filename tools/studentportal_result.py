import requests
from bs4 import BeautifulSoup
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Optional imports for OCR
try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

# Configuration
BASE_URL = "https://sp.srmist.edu.in/srmiststudentportal"
LOGIN_PAGE_URL = f"{BASE_URL}/students/loginManager/youLogin.jsp"
CAPTCHA_URL = f"{BASE_URL}/captchas"
LOGIN_ACTION_URL = f"{BASE_URL}/students/loginManager/youLogin.jsp"
DASHBOARD_URL = f"{BASE_URL}/students/template/HRDSystem.jsp"

# All endpoints
ENDPOINTS = {
    'grades': (f"{BASE_URL}/students/report/studentMarksCredits.jsp", "8"),
    'profile': (f"{BASE_URL}/students/report/studentProfile.jsp", "1"),
    'personal': (f"{BASE_URL}/students/report/studentPersonalDetails.jsp", "17"),
    'subjects': (f"{BASE_URL}/students/report/studentSubjectLists.jsp", "7"),
    'attendance': (f"{BASE_URL}/students/report/studentAttendanceDetails.jsp", "9"),
    'results': (f"{BASE_URL}/students/transaction/onlineResult.jsp", "24"),
    'timetable': (f"{BASE_URL}/students/report/studentTimeTableDetails.jsp", "10"),
    'internal_marks': (f"{BASE_URL}/students/report/studentInternalMarkDetails.jsp", "13"),
    'hall_ticket': (f"{BASE_URL}/students/report/StudentHallticket.jsp", "42")
}

def solve_captcha_fast(image_bytes):
    """Optimized CAPTCHA solver with essential preprocessing techniques"""
    try:
        if not (CV2_AVAILABLE and NUMPY_AVAILABLE and PYTESSERACT_AVAILABLE):
            return ""

        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return ""

        # Resize for better OCR
        img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Essential preprocessing: Adaptive threshold (most effective)
        adaptive = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                         cv2.THRESH_BINARY, 11, 2)

        # Alternative: OTSU threshold with blur
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Try OCR on both variants
        configs = [
            "--psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
            "--psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
        ]

        results = []
        for img_variant in [adaptive, otsu]:
            for config in configs:
                try:
                    text = pytesseract.image_to_string(img_variant, config=config).strip()
                    # Filter for valid captcha format (4-8 alphanumeric chars)
                    if 4 <= len(text) <= 8 and text.isalnum():
                        results.append(text)
                        if len(text) >= 5:  # Return good results immediately
                            return text
                except:
                    continue

        # Return best valid result
        valid_results = [r for r in results if r.isalnum() and 4 <= len(r) <= 8]
        return max(valid_results, key=len) if valid_results else ""

    except:
        return ""

def parse_table_fast(html):
    """Fast table parser"""
    soup = BeautifulSoup(html, 'lxml')
    tables = soup.find_all('table')
    result = []
    
    for table in tables:
        rows = []
        for row in table.find_all('tr'):
            cols = [ele.get_text(strip=True) for ele in row.find_all(['td', 'th'])]
            if cols:
                rows.append(cols)
        if rows:
            result.append(rows)
    
    return result

def fetch_endpoint(session, url, payload, name):
    """Fetch single endpoint"""
    try:
        r = session.post(url, data=payload, timeout=10)
        return name, parse_table_fast(r.text)
    except Exception as e:
        print(f"   ⚠️  {name} failed: {str(e)}")
        return name, []

def scrape_student_portal(netid, password):
    """
    Scrape student data from SRM student portal
    Returns dict with scraped data or error info
    """
    start_time = time.time()
    
    username = netid
    
    print(f"\n{'='*50}")
    print("🔐 Login attempt in progress...")
    print(f"{'='*50}")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": LOGIN_PAGE_URL,
        "Origin": "https://sp.srmist.edu.in"
    })
    
    # Connection pooling for faster requests
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=20,
        pool_maxsize=20,
        max_retries=3
    )
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    MAX_RETRIES = 3  # Reduced from 4 to 3 attempts as requested
    
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🔄 Attempt {attempt}/{MAX_RETRIES}")
        
        try:
            resp = session.get(LOGIN_PAGE_URL, timeout=10)
            resp.raise_for_status()
        except Exception as e:
            print(f"   ✗ Connection error: {str(e)}")
            if attempt == MAX_RETRIES:
                return {"status": "error", "message": f"Connection error: {str(e)}"}
            time.sleep(1)  # Brief pause before retry
            continue
        
        soup = BeautifulSoup(resp.text, 'lxml')
        csrf_val = soup.find(id="hdnCSRF")
        csrf_val = csrf_val.get('value', '') if csrf_val else ""
        
        # Fetch CAPTCHA with retry logic
        captcha_content = None
        for captcha_attempt in range(3):  # Try CAPTCHA up to 3 times
            try:
                captcha_content = session.get(CAPTCHA_URL, timeout=5).content
                if len(captcha_content) > 1000:  # Ensure we got actual image data
                    break
                else:
                    print(f"   ⚠️  CAPTCHA fetch attempt {captcha_attempt + 1} returned small data, retrying...")
                    time.sleep(0.5)  # Wait before retry
            except Exception as e:
                print(f"   ⚠️  CAPTCHA fetch failed (attempt {captcha_attempt + 1}): {str(e)}")
                time.sleep(0.5)
                continue
        
        if not captcha_content or len(captcha_content) < 1000:
            print(f"   ✗ CAPTCHA fetch failed after retries")
            if attempt == MAX_RETRIES:
                return {"status": "error", "message": "Failed to fetch CAPTCHA"}
            continue
        
        # Brief pause to ensure CAPTCHA is ready
        time.sleep(0.2)
        
        # Solve CAPTCHA with retry
        captcha = solve_captcha_fast(captcha_content)
        
        if not captcha or len(captcha) < 4:
            if not (CV2_AVAILABLE and NUMPY_AVAILABLE and PYTESSERACT_AVAILABLE):
                print(f"   ⚠️  CAPTCHA solver unavailable (missing dependencies)")
            else:
                print(f"   ⚠️  CAPTCHA solving failed (attempt {attempt})")
            if attempt == MAX_RETRIES:
                return {
                    "status": "error", 
                    "message": "CAPTCHA solving failed",
                    "details": "Could not solve CAPTCHA after all attempts. Dependencies status: cv2={}, numpy={}, pytesseract={}".format(
                        CV2_AVAILABLE, NUMPY_AVAILABLE, PYTESSERACT_AVAILABLE
                    )
                }
            continue
        
        print(f"   🔤 CAPTCHA solved: {captcha}")
        
        login_payload = {
            "txtAN": username,
            "txtSK": password,
            "hdnCaptcha": captcha,
            "csrfPreventionSalt": csrf_val,
            "txtPageAction": "1",
            "login": "iamalsouser",
            "passwd": "password",
            "hdnCSRF": csrf_val
        }
        
        try:
            post_resp = session.post(LOGIN_ACTION_URL, data=login_payload, timeout=10)
            post_resp.raise_for_status()
        except Exception as e:
            print(f"   ✗ Login POST failed: {str(e)}")
            continue
        
        # Debug: Check response status
        print(f"   → Login response status: {post_resp.status_code}")
        
        if "Invalid Captcha" in post_resp.text:
            print(f"   ⚠️  Invalid CAPTCHA response")
            continue
        
        if "invalid credentials" in post_resp.text.lower():
            print(f"   ✗ Invalid credentials (confirmed by portal)")
            return {"status": "error", "message": "Invalid credentials"}
        
        try:
            dash = session.get(DASHBOARD_URL, timeout=10)
            dash.raise_for_status()
        except Exception as e:
            print(f"   ✗ Dashboard fetch failed: {str(e)}")
            continue
        
        if "logout" in dash.text.lower():
            print("   ✅ LOGIN SUCCESS!")
            
            dash_soup = BeautifulSoup(dash.text, 'lxml')
            subs = dash_soup.find_all(class_="sidenav-footer-subtitle")
            
            student_info = {
                "reg_no": subs[0].get_text(strip=True) if len(subs)>0 else "Unknown",
                "name": subs[1].get_text(strip=True) if len(subs)>1 else "Unknown"
            }
            
            # Scrape Photo URL
            try:
                photo_img = dash_soup.find('img', src=lambda x: x and 'resources/sphotos' in x)
                if photo_img:
                    photo_url_rel = photo_img.get('src')
                    student_info['photo_url'] = urllib.parse.urljoin(DASHBOARD_URL, photo_url_rel)
                else:
                    student_info['photo_url'] = None
            except Exception as e:
                print(f"   ⚠️  Photo scrape failed: {str(e)}")
                student_info['photo_url'] = None
            
            print(f"   👤 Student profile loaded")
            
            csrf_dash = dash_soup.find(id="csrfPreventionSalt")
            csrf_dash = csrf_dash.get('value', '') if csrf_dash else ""
            
            hdnForm = dash_soup.find(id="hdnFormDetails")
            hdnForm = hdnForm.get('value', '1') if hdnForm else "1"
            
            session.headers.update({
                "X-Requested-With": "XMLHttpRequest",
                "Referer": DASHBOARD_URL
            })
            
            base_payload = {
                "filter": "",
                "hdnFormDetails": str(hdnForm),
                "csrfPreventionSalt": csrf_dash
            }
            
            print(f"\n📊 Fetching data (parallel)...")
            fetch_start = time.time()
            
            # Parallel fetching with ThreadPoolExecutor
            results_dict = {}
            with ThreadPoolExecutor(max_workers=9) as executor:
                futures = []
                
                for key, (url, iden) in ENDPOINTS.items():
                    payload = {**base_payload, "iden": iden}
                    future = executor.submit(fetch_endpoint, session, url, payload, key)
                    futures.append(future)
                
                for future in as_completed(futures):
                    name, data = future.result()
                    results_dict[name] = data
                    print(f"   ✅ {name}: {len(data)} tables")
            
            fetch_time = time.time() - fetch_start
            total_time = time.time() - start_time
            
            print(f"\n⚡ Fetch time: {fetch_time:.2f}s")
            print(f"⚡ Total time: {total_time:.2f}s")
            
            final_data = {
                "status": "success",
                "student_info": student_info,
                "dashboard_info": results_dict.get('profile', []),
                "personal_details": results_dict.get('personal', []),
                "subjects_offered": results_dict.get('subjects', []),
                "attendance_details": results_dict.get('attendance', []),
                "semester_results": results_dict.get('results', []),
                "timetable": results_dict.get('timetable', []),
                "internal_marks": results_dict.get('internal_marks', []),
                "hall_ticket": results_dict.get('hall_ticket', []),
                "raw_tables": results_dict.get('grades', []),
                "performance": {
                    "fetch_time_seconds": round(fetch_time, 2),
                    "total_time_seconds": round(total_time, 2),
                    "parallel_requests": 9
                }
            }
            
            return final_data
        
        else:
            # Didn't find logout button - login may have failed or session invalid
            print(f"   ⚠️  No logout button found in dashboard (login may have failed)")
            if attempt == MAX_RETRIES:
                return {
                    "status": "error", 
                    "message": "Login failed after 3 attempts",
                    "details": "Could not authenticate with provided credentials. Possible causes: Invalid credentials, CAPTCHA solving failed, or portal temporarily unavailable.",
                    "dependencies_available": {
                        "cv2": CV2_AVAILABLE,
                        "numpy": NUMPY_AVAILABLE,
                        "pytesseract": PYTESSERACT_AVAILABLE
                    }
                }
    
    return {
        "status": "error", 
        "message": "Max retries exceeded",
        "details": "Failed to login after 3 retry attempts"
    }