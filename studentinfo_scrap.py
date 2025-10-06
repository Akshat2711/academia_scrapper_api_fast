import requests
import json
import re
from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup


class AcademiaClient:
    """Client for interacting with SRM Academia portal"""
    
    BASE_URL = "https://academia.srmist.edu.in"
    
    def __init__(self, email: str, password: str):
        """
        Initialize the Academia client
        
        Args:
            email: User email address
            password: User password
        """
        self.email = email
        self.password = password
        self.session = requests.Session()
        self.identifier = None
        self.digest = None
        self._setup_session()
    
    def _setup_session(self):
        """Set up session with user agent and initial cookies"""
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        initial_cookies = {
            '_uetvid': 'b3000840e89c11ef8036e75565fa990c',
            '_ga_S234BK01XY': 'GS1.3.1745294863.2.0.1745294863.60.0.0',
            '_ga_QNCRQG0GFE': 'GS2.1.s1756038219$o13$g1$t1756038490$j58$l0$h0',
            '_ga': 'GA1.3.390342211.1722929679',
            '_gid': 'GA1.3.2113967629.1759126016',
            'zalb_74c3a1eecc': '62cd2f9337f58b07cdaa2f90f0ac1087',
            'zccpn': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            '_zcsr_tmp': 'da3eb9d9-c3f1-418c-a4a7-30a74a3aec85',
            'JSESSIONID': '7A17742FC60777CB72F1A41EE40E757F',
            'cli_rgn': 'IN',
            'zalb_f0e8db9d3d': '983d6a65b2f29022f18db52385bfc639',
            'iamcsr': '391788bd-2546-4716-8132-fe456c9b066a',
            'stk': 'c799c6752fa5adf5621357e8bbc0b925',
            '_ga_HQWPLLNMKY': 'GS2.3.s1759165956$o23$g0$t1759165956$j60$l0$h0'
        }
        self.session.cookies.update(initial_cookies)
    
    def _get_common_headers(self) -> Dict[str, str]:
        """Get common headers for requests"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',
            'Origin': f'{self.BASE_URL}',
            'Referer': f'{self.BASE_URL}/accounts/p/10002227248/signin',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-ZCSRF-TOKEN': 'iamcsrcoo=391788bd-2546-4716-8132-fe456c9b066a',
            'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
        }
    
    def lookup_user(self) -> bool:
        """Perform user lookup to get identifier and digest"""
        print("Step 1: Performing user lookup...")
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/lookup/{self.email}'
        data = {
            'mode': 'primary',
            'cli_time': '1759165956409',
            'orgtype': '40',
            'servicename': 'ZohoCreator',
            'service_language': 'en',
            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'
        }
        
        try:
            response = self.session.post(url, headers=self._get_common_headers(), data=data)
            response.raise_for_status()
            
            lookup_data = response.json()
            self.identifier = lookup_data.get('lookup', {}).get('identifier')
            self.digest = lookup_data.get('lookup', {}).get('digest')
            
            if self.identifier and self.digest:
                print(f"✓ Lookup successful\n")
                return True
            else:
                print("✗ Failed to get user identifier or digest\n")
                return False
                
        except Exception as e:
            print(f"✗ Lookup failed: {str(e)}\n")
            return False
    
    def login(self) -> bool:
        """Login with password using digest from lookup"""
        if not self.identifier or not self.digest:
            print("✗ No identifier/digest found. Run lookup_user() first.\n")
            return False
        
        print("Step 2: Logging in...")
        
        url = f'{self.BASE_URL}/accounts/p/40-10002227248/signin/v2/primary/{self.identifier}/password'
        params = {
            'digest': self.digest,
            'cli_time': '1759165956409',
            'orgtype': '40',
            'servicename': 'ZohoCreator',
            'service_language': 'en',
            'serviceurl': f'{self.BASE_URL}/portal/academia-academic-services/redirectFromLogin'
        }
        
        body = json.dumps({
            "passwordauth": {
                "password": self.password
            }
        })
        
        try:
            response = self.session.post(url, headers=self._get_common_headers(), params=params, data=body)
            response.raise_for_status()
            
            login_data = response.json()
            
            if login_data.get('passwordauth', {}).get('code') == 'SIGIN_SUCCESS':
                print("✓ Login successful!\n")
                return True
            else:
                print("✗ Login failed!\n")
                return False
                
        except Exception as e:
            print(f"✗ Login failed: {str(e)}\n")
            return False
    
    def _get_page_headers(self) -> Dict[str, str]:
        """Get headers for page requests"""
        return {
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-US,en;q=0.9,en-IN;q=0.8',
            'Referer': f'{self.BASE_URL}/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'X-Requested-With': 'XMLHttpRequest'
        }
    
    def parse_attendance(self, html_content: str) -> Dict[str, Any]:
        """Parse attendance HTML to structured JSON matching desired format"""
        
        # Extract from the JavaScript escaped content
        match = re.search(r"innerHTML = pageSanitizer\.sanitize\('(.+?)'\);", html_content, re.DOTALL)
        if not match:
            return {"error": "Could not parse HTML"}
        
        # Unescape the JavaScript string
        escaped_html = match.group(1)
        html_decoded = escaped_html.encode().decode('unicode_escape')
        
        soup = BeautifulSoup(html_decoded, 'html.parser')
        
        data = {
            "student_info": {},
            "attendance": {
                "courses": {},
                "overall_attendance": 0.0,
                "total_hours_conducted": 0,
                "total_hours_absent": 0
            },
            "marks": {},
            "summary": {}
        }
        
        # Parse student information
        info_rows = soup.find_all('tr')
        for row in info_rows:
            cells = row.find_all('td')
            if len(cells) >= 2:
                key_text = cells[0].get_text(strip=True).replace(':', '')
                value_text = cells[1].get_text(strip=True)
                
                if key_text == 'Registration Number':
                    data['student_info']['registration_number'] = value_text
                elif key_text == 'Name':
                    data['student_info']['name'] = value_text
                elif key_text == 'Program':
                    data['student_info']['program'] = value_text
                elif key_text == 'Department':
                    data['student_info']['department'] = value_text
                elif key_text == 'Specialization':
                    data['student_info']['specialization'] = value_text
                elif key_text == 'Semester':
                    data['student_info']['semester'] = value_text
                elif key_text == 'Batch':
                    data['student_info']['batch'] = value_text
                elif key_text == 'Feedback Status':
                    data['student_info']['feedback_status'] = value_text
                elif key_text == 'Enrollment Status / DOE':
                    parts = value_text.split(' / ')
                    if len(parts) == 2:
                        data['student_info']['enrollment_status'] = parts[0]
                        data['student_info']['enrollment_date'] = parts[1]
                elif key_text == 'Photo-ID':
                    img_tag = cells[1].find('img')
                    if img_tag and img_tag.get('src'):
                        data['student_info']['photo_url'] = img_tag.get('src')
        
        # Parse attendance courses
        attendance_table = soup.find('table', {'bgcolor': '#FAFAD2'})
        if attendance_table:
            rows = attendance_table.find_all('tr')[1:]  # Skip header
            total_conducted = 0
            total_absent = 0
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 9:
                    course_code_raw = cells[0].get_text(strip=True)
                    # Extract course code (e.g., "21CSC302J" from "21CSC302J\nRegular")
                    course_code_parts = course_code_raw.split('\n')
                    course_code = course_code_parts[0]
                    registration_type = course_code_parts[1] if len(course_code_parts) > 1 else ''

                    # Get category to make truly unique key
                    category = cells[2].get_text(strip=True)

                    # Create unique key using course_code + category
                    course_key = course_code + category
                    
                    hours_conducted = int(cells[6].get_text(strip=True))
                    hours_absent = int(cells[7].get_text(strip=True))
                    
                    total_conducted += hours_conducted
                    total_absent += hours_absent
                    
                    data['attendance']['courses'][course_key] = {
                        'course_title': cells[1].get_text(strip=True),
                        'category': cells[2].get_text(strip=True),
                        'faculty_name': cells[3].get_text(strip=True),
                        'slot': cells[4].get_text(strip=True),
                        'room_no': cells[5].get_text(strip=True),
                        'hours_conducted': hours_conducted,
                        'hours_absent': hours_absent,
                        'attendance_percentage': float(cells[8].get_text(strip=True))
                    }
            
            # Calculate overall attendance
            if total_conducted > 0:
                data['attendance']['overall_attendance'] = round(
                    ((total_conducted - total_absent) / total_conducted) * 100, 2
                )
            data['attendance']['total_hours_conducted'] = total_conducted
            data['attendance']['total_hours_absent'] = total_absent
        
        # Parse internal marks
        marks_tables = soup.find_all('table', {'border': '1'})
        for table in marks_tables:
            if 'Course Code' in table.get_text() and 'Test Performance' in table.get_text():
                rows = table.find_all('tr')[1:]  # Skip header
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) >= 3:
                        course_code = cells[0].get_text(strip=True)
                        course_type = cells[1].get_text(strip=True)
                        
                        # Create unique key using course_code + course_type
                        marks_key = course_code + course_type
                        
                        # Parse test performance
                        performance_cell = cells[2]
                        tests = []
                        inner_table = performance_cell.find('table')
                        if inner_table:
                            inner_rows = inner_table.find_all('tr')
                            for inner_row in inner_rows:
                                inner_cells = inner_row.find_all('td')
                                for inner_cell in inner_cells:
                                    # Get all text content
                                    text = inner_cell.get_text(separator='\n', strip=True)
                                    lines = [line.strip() for line in text.split('\n') if line.strip()]
                                    
                                    # Parse test name and score
                                    if len(lines) >= 2:
                                        test_name_line = lines[0]  # e.g., "FT-I/5.00"
                                        score_line = lines[1]       # e.g., "5.00" or "3.40"
                                        
                                        # Extract test name and max marks
                                        if '/' in test_name_line:
                                            test_parts = test_name_line.split('/')
                                            test_name = test_parts[0]
                                            max_marks = float(test_parts[1])
                                            obtained_marks = float(score_line)
                                            
                                            tests.append({
                                                'test_name': test_name,
                                                'obtained_marks': obtained_marks,
                                                'max_marks': max_marks,
                                                'percentage': round((obtained_marks / max_marks) * 100, 2) if max_marks > 0 else 0.0
                                            })
                        
                        # Add to marks dict with unique key
                        data['marks'][marks_key] = {
                            'course_type': course_type,
                            'tests': tests
                        }
        
        return data
    
    def parse_timetable(self,html_content: str) -> Dict[str, Any]:
        """Parse timetable HTML to structured JSON with course information"""
        
        # Extract from the JavaScript escaped content
        match = re.search(r"innerHTML = pageSanitizer\.sanitize\('(.+?)'\);", html_content, re.DOTALL)
        if not match:
            return {"error": "Could not parse HTML"}
        
        # Unescape the JavaScript string - handle \xNN hex escapes
        escaped_html = match.group(1)
        
        # Replace hex escapes like \x3C with actual characters
        def decode_hex(match):
            return chr(int(match.group(1), 16))
        
        html_decoded = re.sub(r'\\x([0-9a-fA-F]{2})', decode_hex, escaped_html)
        
        soup = BeautifulSoup(html_decoded, 'html.parser')
        
        data = {
            "student_info": {
                "registration_number": "",
                "name": "",
                "batch": "",
                "mobile": "",
                "program": "",
                "department": "",
                "semester": ""
            },
            "courses": [],
            "advisors": {},
            "total_credits": 0
        }
        
        # Parse student information
        all_tables = soup.find_all('table')
        for table in all_tables:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                for i in range(0, len(cells)-1, 2):
                    if i+1 >= len(cells):
                        break
                    label = cells[i].get_text(strip=True).replace(':', '')
                    value = cells[i+1].get_text(separator=' ', strip=True)
                    value = re.sub(r'\s+', ' ', value)
                    
                    if 'Registration Number' in label:
                        data['student_info']['registration_number'] = value
                    elif label == 'Name':
                        data['student_info']['name'] = value
                    elif label == 'Batch':
                        data['student_info']['batch'] = re.sub(r'[^0-9]', '', value)
                    elif label == 'Mobile':
                        data['student_info']['mobile'] = value
                    elif label == 'Program':
                        data['student_info']['program'] = value
                    elif 'Department' in label:
                        data['student_info']['department'] = value
                    elif label == 'Semester':
                        data['student_info']['semester'] = value
        
        # Find and parse course data using regex from the decoded HTML
        # Pattern to match course rows: </tr><td>NUMBER</td><td>CODE</td>...
        course_pattern = r'<td>(\d+)</td><td>([^<]+)</td><td>([^<]+)</td><td>(\d+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td[^>]*>([^<]+)</td><td>([^<]*)</td><td>([^<]+)</td>'
        
        courses_found = re.findall(course_pattern, html_decoded)
        
        for course_data in courses_found:
            try:
                s_no, course_code, course_title, credit, regn_type, category, course_type, faculty_name, slot, room_no, academic_year = course_data
                
                credit_val = int(credit) if credit.isdigit() else 0
                
                course = {
                    's_no': s_no,
                    'course_code': course_code.strip(),
                    'course_title': course_title.strip(),
                    'credit': credit_val,
                    'regn_type': regn_type.strip(),
                    'category': category.strip(),
                    'course_type': course_type.strip(),
                    'faculty_name': faculty_name.strip(),
                    'slot': slot.strip(),
                    'room_no': room_no.strip(),
                    'academic_year': academic_year.strip()
                }
                
                data['courses'].append(course)
                data['total_credits'] += credit_val
                
            except Exception as e:
                print(f"Error parsing course: {e}")
                continue
        
        # Parse advisors
        for table in soup.find_all('table'):
            cells = table.find_all('td', {'align': 'center'})
            for cell in cells:
                full_text = cell.get_text(separator='\n', strip=True)
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                if any('Faculty Advisor' in line for line in lines):
                    advisor_idx = next((i for i, line in enumerate(lines) if 'Faculty Advisor' in line), -1)
                    if advisor_idx > 0:
                        data['advisors']['faculty_advisor'] = {
                            'name': lines[advisor_idx - 1],
                            'email': next((line for line in lines if '@srmist.edu.in' in line), ''),
                            'phone': next((line for line in lines if line.replace('-','').isdigit() and len(line.replace('-','')) >= 10), '')
                        }
                elif any('Academic Advisor' in line for line in lines):
                    advisor_idx = next((i for i, line in enumerate(lines) if 'Academic Advisor' in line), -1)
                    if advisor_idx > 0:
                        data['advisors']['academic_advisor'] = {
                            'name': lines[advisor_idx - 1],
                            'email': next((line for line in lines if '@srmist.edu.in' in line), ''),
                            'phone': next((line for line in lines if line.replace('-','').isdigit() and len(line.replace('-','')) >= 10), '')
                        }
        
        return data
    def get_attendance(self) -> Optional[Dict[str, Any]]:
        """Fetch and parse attendance data"""
        print("Fetching attendance data...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/My_Attendance'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            print(f"✓ Attendance data retrieved (Status: {response.status_code})\n")
            return self.parse_attendance(response.text)
                
        except Exception as e:
            print(f"✗ Failed to fetch attendance: {str(e)}\n")
            return None
    
    def get_timetable(self) -> Optional[Dict[str, Any]]:
        """Fetch and parse timetable data"""
        print("Fetching timetable data...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/My_Time_Table_2023_24'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            print(f"✓ Timetable data retrieved (Status: {response.status_code})\n")
            return self.parse_timetable(response.text)
                
        except Exception as e:
            print(f"✗ Failed to fetch timetable: {str(e)}\n")
            return None
        
    def get_day_order(self) -> Optional[int]:
        """Fetch current day order from welcome page"""
        print("Fetching day order...")
        
        url = f'{self.BASE_URL}/srm_university/academia-academic-services/page/WELCOME'
        
        try:
            response = self.session.get(url, headers=self._get_page_headers())
            response.raise_for_status()
            
            # Search for day order pattern in the response
            # Pattern: \x3EDay\x20Order\x3A1\x26nbsp\x3B or similar variations
            match = re.search(r'Day\\x20Order\\x3A(\d+)', response.text)
            
            if match:
                day_order = int(match.group(1))
                print(f"✓ Day Order retrieved: {day_order}\n")
                return day_order
            else:
                print("✗ Could not find day order in response\n")
                return None
                
        except Exception as e:
            print(f"✗ Failed to fetch day order: {str(e)}\n")
            return None


def main():
    """Main execution function"""
    
    # Configuration
    EMAIL = "your_email@srmist.edu.in"
    PASSWORD = "password123"
    
    # Create client instance
    client = AcademiaClient(EMAIL, PASSWORD)
    
    # Step 1: Lookup user
    if not client.lookup_user():
        return
    
    # Step 2: Login
    if not client.login():
        return
    
    # Step 3a: Fetch day order
    day_order = client.get_day_order()

    # Step 3b: Fetch and parse attendance
    attendance_data = client.get_attendance()
    if attendance_data and day_order is not None:
        attendance_data['day_order'] = day_order
        
    if attendance_data:
        print("\n" + "="*50)
        print("COMPLETE STUDENT DATA")
        print("="*50)
        print(json.dumps(attendance_data, indent=2))
    
    # Step 4: Fetch and parse timetable
    timetable_data = client.get_timetable()
    if timetable_data:
        print("\n" + "="*50)
        print("TIMETABLE DATA")
        print("="*50)
        print(json.dumps(timetable_data, indent=2))


if __name__ == "__main__":
    main()