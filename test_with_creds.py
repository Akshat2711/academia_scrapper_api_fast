import requests
import json
import sys

# Force encoding to utf-8 for console output
sys.stdout.reconfigure(encoding='utf-8')

url = 'http://127.0.0.1:8000/scrape'
payload = {
    'email': 'gn1189@srmist.edu.in',
    'password': 'Jsyupii24k.'
}

print(f"Testing {url} with user provided credentials...")

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Success!")
        print(f"Keys returned: {list(data.keys())}")
        if 'attendance' in data:
            att = data['attendance']
            print(f"Attendance Data Type: {type(att)}")
            if isinstance(att, dict) and 'attendance_data' in att:
                 print(f"Number of subjects: {len(att['attendance_data'])}")
        if 'timetable' in data:
             print("Timetable data present.")
    else:
        print("Request failed.")
        print(response.text)

except Exception as e:
    print(f"An error occurred: {e}")
