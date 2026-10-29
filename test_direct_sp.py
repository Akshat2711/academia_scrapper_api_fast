import ddddocr, requests, base64, re, time, json
from bs4 import BeautifulSoup

ocr = ddddocr.DdddOcr(show_ad=False)
s = requests.Session()
login_page_url = 'https://sp.srmist.edu.in/srmiststudentportal/students/loginManager/youLogin.jsp'
login_action_url = 'https://sp.srmist.edu.in/srmiststudentportal/LoginServlet'
dashboard_url = 'https://sp.srmist.edu.in/srmiststudentportal/students/template/HRDSystem.jsp'

ua = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
headers = {
    'User-Agent': ua,
    'Origin': 'https://sp.srmist.edu.in',
    'Referer': login_page_url,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}

start_time = int(time.time() * 1000)
print('1. Getting login page...')
r = s.get(login_page_url, headers=headers)
body = r.text

token_match = re.search(r'SCaptchaServlet\?ts=.*?token=([a-z0-9\-]+)', body, re.I)
nonce_match = re.search(r"nonce:\s*'([^']+)'", body)
domain_match = re.search(r"window\.SECURE_CONFIG\.domainFieldName\s*=\s*'([^']+)'", body)
captcha_field_match = re.search(r"window\.SECURE_CONFIG\.captchaFieldName\s*=\s*'([^']+)'", body)
delim_match = re.search(r"window\.SECURE_CONFIG\.randomDelimiter\s*=\s*'([^']+)'", body)
honeypot_match = re.search(r'name="(ph_[a-z0-9]+)"', body)

token = token_match.group(1)
nonce = nonce_match.group(1) if nonce_match else ''
domain_field = domain_match.group(1) if domain_match else ''
captcha_field = captcha_field_match.group(1) if captcha_field_match else ''
delim = delim_match.group(1) if delim_match else ''
honeypot = honeypot_match.group(1) if honeypot_match else ''

# Fetch Captcha
ts = int(time.time() * 1000)
img_headers = dict(headers)
if nonce:
    img_headers['X-Domain-Proof'] = base64.b64encode(f'{nonce}:sp.srmist.edu.in'.encode()).decode()

img_resp = s.get(f'https://sp.srmist.edu.in/srmiststudentportal/SCaptchaServlet?ts={ts}&token={token}', headers=img_headers)
solved_captcha = ocr.classification(img_resp.content).strip()
print(f'2. Solved Captcha: {solved_captcha}')

time.sleep(3) # Human typing delay

now = int(time.time() * 1000)
telemetry = {
    'startTime': start_time,
    'currentDomain': 'sp.srmist.edu.in',
    'timezoneOffset': -330,
    'screenWidth': 1920,
    'screenHeight': 1080,
    'colorDepth': 24,
    'devicePixelRatio': 1.25,
    'platform': 'Win32',
    'userAgent': ua,
    'language': 'en-US',
    'hardwareConcurrency': 8,
    'deviceMemory': 8,
    'touchSupport': False,
    'webdriver': False,
    'mouseClicks': 4,
    'mouseMovements': 18,
    'keystrokeCount': 16,
    'typingSpeedMs': 2500,
    'canvasHash': '82f1b4a',
    'submitTime': now,
    'timeOnPageMs': now - start_time,
}
telemetry_b64 = base64.b64encode(json.dumps(telemetry).encode('utf-8')).decode('utf-8')

payload = {
    'username': 'nk1629',
    'password': 'Srmlol@700',
    'captcha': solved_captcha,
    'telemetryPayload': telemetry_b64,
    'fpPayload': '',
    'fpToken': '',
    'recaptchaToken': '',
}
if honeypot:
    payload[honeypot] = ''
if domain_field:
    payload[domain_field] = base64.b64encode(b'ni.ude.tsimrs.ps').decode()
if captcha_field:
    elapsed_secs = int((now - start_time) / 1000)
    trap_str = f'{elapsed_secs}{delim}18'
    payload[captcha_field] = base64.b64encode(trap_str.encode()).decode()

post_resp = s.post(login_action_url, data=payload, headers=headers)
print('post_resp status:', post_resp.status_code)
print('post_resp cookies:', s.cookies.get_dict())
with open('post_resp.html', 'w', encoding='utf-8') as f:
    f.write(post_resp.text)

dash_resp = s.get(dashboard_url, headers=headers)
with open('dash_resp.html', 'w', encoding='utf-8') as f:
    f.write(dash_resp.text)

print('post_resp title:', BeautifulSoup(post_resp.text, 'html.parser').title)
print('dash_resp title:', BeautifulSoup(dash_resp.text, 'html.parser').title)
print('dash_resp url:', dash_resp.url)




