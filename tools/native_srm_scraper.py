import requests
import json
import base64
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup

try:
    import ddddocr
    _ocr_instance = ddddocr.DdddOcr(show_ad=False)
except Exception as e:
    _ocr_instance = None
    print(f"Warning: ddddocr initialization failed: {e}")

BASE_URL = "https://sp.srmist.edu.in/srmiststudentportal"
LOGIN_PAGE_URL = f"{BASE_URL}/students/loginManager/youLogin.jsp"
LOGIN_ACTION_URL = f"{BASE_URL}/LoginServlet"
DASHBOARD_URL = f"{BASE_URL}/students/template/HRDSystem.jsp"
ATTENDANCE_URL = f"{BASE_URL}/students/report/studentAttendanceDetails.jsp"
MARKS_URL = f"{BASE_URL}/students/report/studentInternalMarkDetails.jsp"
MARKS_INNER_URL = f"{BASE_URL}/students/report/studentInternalMarkDetailsInner.jsp"

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

def _solve_captcha_bytes(img_bytes: bytes) -> str:
    if not _ocr_instance:
        return ""
    try:
        res = _ocr_instance.classification(img_bytes)
        return res.strip() if res else ""
    except Exception as e:
        print(f"Captcha classification error: {e}")
        return ""

def _fetch_component_marks(session: requests.Session, subject_id: str, code: str, title: str, status_val: str, headers: dict):
    payload = {
        "iden": "1",
        "hdnSubjectId": str(subject_id),
        "status": str(status_val)
    }
    tests = []
    try:
        resp = session.post(MARKS_INNER_URL, data=payload, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                    if len(cells) >= 3 and '/' in cells[2] and cells[0] != 'Entered on':
                        test_name = cells[1]
                        mark_part = cells[2]
                        try:
                            parts = mark_part.split('/')
                            got = float(parts[0].strip())
                            tot = float(parts[1].strip())
                            pct = round((got / tot) * 100, 2) if tot > 0 else 0.0
                            tests.append({
                                'test_name': test_name,
                                'obtained_marks': got,
                                'max_marks': tot,
                                'percentage': pct,
                            })
                        except Exception:
                            pass
    except Exception as e:
        print(f"Failed to fetch component marks for {code}: {e}")
    return code, tests

def scrape_srm_student_portal(netid: str, password: str, max_retries: int = 3):
    """
    Direct first-party scraper for SRM Student Portal (sp.srmist.edu.in).
    Uses ddddocr for 0-friction fast CAPTCHA solving.
    Returns: (dict_data, error_message)
    """
    clean_net_id = netid.strip().split('@')[0].strip()
    
    for attempt in range(1, max_retries + 1):
        try:
            session = requests.Session()
            std_headers = {
                'User-Agent': USER_AGENT,
                'Origin': 'https://sp.srmist.edu.in',
                'Referer': LOGIN_PAGE_URL,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
            }

            start_time = int(time.time() * 1000)
            page_resp = session.get(LOGIN_PAGE_URL, headers=std_headers, timeout=10)
            body = page_resp.text

            token_m = re.search(r'SCaptchaServlet\?ts=.*?token=([a-z0-9\-]+)', body, re.I)
            if not token_m:
                continue
            token = token_m.group(1)

            nonce_m = re.search(r"nonce:\s*'([^']+)'", body)
            nonce = nonce_m.group(1) if nonce_m else ''

            domain_m = re.search(r"window\.SECURE_CONFIG\.domainFieldName\s*=\s*'([^']+)'", body)
            domain_field = domain_m.group(1) if domain_m else ''

            captcha_field_m = re.search(r"window\.SECURE_CONFIG\.captchaFieldName\s*=\s*'([^']+)'", body)
            captcha_field = captcha_field_m.group(1) if captcha_field_m else ''

            delim_m = re.search(r"window\.SECURE_CONFIG\.randomDelimiter\s*=\s*'([^']+)'", body)
            delim = delim_m.group(1) if delim_m else ''

            honeypot_m = re.search(r'name="(ph_[a-z0-9]+)"', body)
            honeypot = honeypot_m.group(1) if honeypot_m else ''

            # Fetch Captcha image
            img_headers = dict(std_headers)
            if nonce:
                img_headers['X-Domain-Proof'] = base64.b64encode(f"{nonce}:sp.srmist.edu.in".encode()).decode()

            ts = int(time.time() * 1000)
            img_resp = session.get(f"{BASE_URL}/SCaptchaServlet?ts={ts}&token={token}", headers=img_headers, timeout=10)
            if img_resp.status_code != 200 or len(img_resp.content) < 300:
                continue

            solved_captcha = _solve_captcha_bytes(img_resp.content)
            if not solved_captcha or len(solved_captcha) < 4:
                continue

            # Human-like delay (min 2.2 seconds) to satisfy portal's anti-bot time thresholds
            elapsed_delay = (time.time() * 1000) - start_time
            if elapsed_delay < 2300:
                time.sleep((2300 - elapsed_delay) / 1000.0)

            now = int(time.time() * 1000)
            time_on_page = now - start_time

            telemetry = {
                'startTime': start_time,
                'currentDomain': 'sp.srmist.edu.in',
                'timezoneOffset': -330,
                'screenWidth': 1920,
                'screenHeight': 1080,
                'colorDepth': 24,
                'devicePixelRatio': 1.25,
                'platform': 'Win32',
                'userAgent': USER_AGENT,
                'language': 'en-US',
                'hardwareConcurrency': 8,
                'deviceMemory': 8,
                'touchSupport': False,
                'webdriver': False,
                'mouseClicks': 4,
                'mouseMovements': 18,
                'keystrokeCount': 16,
                'typingSpeedMs': 2450,
                'canvasHash': '82f1b4a',
                'submitTime': now,
                'timeOnPageMs': time_on_page,
            }
            telemetry_b64 = base64.b64encode(json.dumps(telemetry).encode('utf-8')).decode('utf-8')

            login_payload = {
                'username': clean_net_id,
                'password': password.strip(),
                'captcha': solved_captcha,
                'telemetryPayload': telemetry_b64,
                'fpPayload': '',
                'fpToken': '',
                'recaptchaToken': '',
            }
            if honeypot:
                login_payload[honeypot] = ''
            if domain_field:
                login_payload[domain_field] = base64.b64encode(b'ni.ude.tsimrs.ps').decode()
            if captcha_field:
                elapsed_secs = int(time_on_page / 1000)
                login_payload[captcha_field] = base64.b64encode(f"{elapsed_secs}{delim}18".encode()).decode()

            post_resp = session.post(LOGIN_ACTION_URL, data=login_payload, headers=std_headers, timeout=12)
            post_soup = BeautifulSoup(post_resp.text, 'html.parser')
            alert = post_soup.find(class_='alert')
            if alert:
                alert_text = alert.get_text(strip=True)
                if 'captcha' in alert_text.lower():
                    print(f"Attempt {attempt}: Invalid CAPTCHA ('{solved_captcha}'), retrying...")
                    continue
                clean_alert = re.sub(r'^Alert\s*', '', alert_text, flags=re.I).strip()
                return None, clean_alert

            # Check if login succeeded
            subs = post_soup.find_all(class_='sidenav-footer-subtitle')
            is_logged_in = len(subs) > 0 or 'logout' in post_resp.text.lower()
            if not is_logged_in:
                # Try checking dashboard url directly
                dash_check = session.get(DASHBOARD_URL, headers=std_headers, timeout=10)
                post_soup = BeautifulSoup(dash_check.text, 'html.parser')
                subs = post_soup.find_all(class_='sidenav-footer-subtitle')
                is_logged_in = len(subs) > 0 or 'logout' in dash_check.text.lower()

            if not is_logged_in:
                print(f"Attempt {attempt}: Login response did not contain user profile. Text snippet: {post_resp.text[:200]!r}, retrying...")
                continue

            reg_no = subs[0].get_text(strip=True) if len(subs) > 0 else clean_net_id
            name = subs[1].get_text(strip=True) if len(subs) > 1 else clean_net_id

            photo_img = post_soup.find('img', src=lambda x: x and 'sphotos' in x)
            photo_url = urllib.parse.urljoin(DASHBOARD_URL, photo_img.get('src')) if photo_img else None

            # Setup AJAX headers for data retrieval
            ajax_headers = dict(std_headers)
            ajax_headers['X-Requested-With'] = 'XMLHttpRequest'
            ajax_headers['Referer'] = DASHBOARD_URL

            # 1. Fetch Attendance (iden=9) & Marks (iden=13) in parallel
            att_payload = {
                'iden': '9',
                'filter': '',
                'hdnFormDetails': '1',
                'csrfPreventionSalt': ''
            }
            marks_payload = {
                'iden': '13',
                'filter': '',
                'hdnFormDetails': '1',
                'csrfPreventionSalt': ''
            }
            with ThreadPoolExecutor(max_workers=2) as init_exec:
                f_att = init_exec.submit(session.post, ATTENDANCE_URL, data=att_payload, headers=ajax_headers, timeout=10)
                f_marks = init_exec.submit(session.post, MARKS_URL, data=marks_payload, headers=ajax_headers, timeout=10)
                att_resp = f_att.result()
                marks_resp = f_marks.result()

            courses = {}
            tot_hours = 0
            tot_absent = 0

            if att_resp.status_code == 200:
                att_soup = BeautifulSoup(att_resp.text, 'html.parser')
                tables = att_soup.find_all('table')
                if tables:
                    for row in tables[0].find_all('tr'):
                        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        if len(cells) >= 6 and cells[0] != 'Code' and cells[0]:
                            code = cells[0].strip()
                            title = cells[1].strip()
                            try:
                                max_h = int(cells[2])
                                att_h = int(cells[3])
                                abs_h = int(cells[4])
                                pct = float(cells[5])
                            except ValueError:
                                continue

                            tot_hours += max_h
                            tot_absent += abs_h

                            margin = max(0, int(att_h / 0.75 - max_h)) if max_h > 0 else 0
                            required = max(0, int((0.75 * max_h - att_h) / 0.25)) if (max_h > 0 and pct < 75.0) else 0

                            course_type = 'Theory & Practical' if 'J' in code else ('Practical' if 'P' in code else 'Theory')
                            course_key = code + ('Theory' if 'T' in code or 'J' in code else 'Practical')

                            courses[course_key] = {
                                'course_code': code,
                                'course_title': title,
                                'category': 'General',
                                'course_type': course_type,
                                'hours_conducted': max_h,
                                'hours_absent': abs_h,
                                'attendance_percentage': round(pct, 2),
                                'margin': margin,
                                'required': required,
                            }

            overall_pct = ((tot_hours - tot_absent) / tot_hours * 100) if tot_hours > 0 else 0.0

            attendance_data = {
                'overall_attendance': round(overall_pct, 2),
                'total_hours_conducted': tot_hours,
                'total_hours_absent': tot_absent,
                'courses': courses,
                'attendance_unavailable': False if len(courses) > 0 else True,
            }

            # 2. Parse Internal Marks (fetched in parallel above)
            marks_data = {}

            if marks_resp.status_code == 200:
                marks_soup = BeautifulSoup(marks_resp.text, 'html.parser')
                marks_tables = marks_soup.find_all('table')
                
                course_marks_meta = []
                if marks_tables:
                    for row in marks_tables[0].find_all('tr'):
                        cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                        if len(cells) >= 3 and cells[0] != 'Code' and cells[0]:
                            code = cells[0].strip()
                            name_str = cells[1].strip()
                            tot_str = cells[2].strip()
                            got = 0.0
                            tot = 0.0
                            if '/' in tot_str:
                                p = tot_str.split('/')
                                try:
                                    got = float(p[0].strip())
                                    tot = float(p[1].strip())
                                except ValueError:
                                    pass

                            c_type = 'Theory' if 'T' in code or 'J' in code else 'Practical'
                            marks_key = code + c_type
                            marks_data[marks_key] = {
                                'course_code': code,
                                'course_name': name_str,
                                'course_type': c_type,
                                'tests': [],
                                'total_mark_got': got,
                                'total_marks': tot,
                            }

                # Find all funViewComponentWiseMarks calls in HTML to get inner test details
                inner_calls = re.findall(r"funViewComponentWiseMarks\s*\(\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*([0-9]+)\s*\)", marks_resp.text)
                if inner_calls:
                    with ThreadPoolExecutor(max_workers=min(len(inner_calls), 8)) as executor:
                        future_to_code = {
                            executor.submit(_fetch_component_marks, session, call[0], call[1], call[2], call[3], ajax_headers): call[1]
                            for call in inner_calls
                        }
                        for future in as_completed(future_to_code):
                            try:
                                c_code, c_tests = future.result()
                                c_type = 'Theory' if 'T' in c_code or 'J' in c_code else 'Practical'
                                marks_key = c_code + c_type
                                if marks_key in marks_data:
                                    marks_data[marks_key]['tests'] = c_tests
                            except Exception as ex:
                                print(f"Error fetching component marks: {ex}")

            result_dict = {
                'status': 'success',
                'student_info': {
                    'reg_no': reg_no,
                    'name': name,
                    'photo_url': photo_url,
                },
                'attendance': attendance_data,
                'marks': marks_data,
            }
            return result_dict, None

        except Exception as e:
            print(f"Attempt {attempt} exception: {e}")
            if attempt == max_retries:
                return None, str(e)
            time.sleep(1)

    return None, "Failed to login and fetch data after max retries"
