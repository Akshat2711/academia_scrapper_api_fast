import re
from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup


#helper fnc for parsing attendance data 
def parse_attendance(html_content: str) -> Dict[str, Any]:
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
                    'attendance_percentage': float(cells[8].get_text(strip=True)) if cells[8].get_text(strip=True).replace('.','').isdigit() else 0.0
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
                                        max_marks = float(test_parts[1]) if test_parts[1].replace('.','').replace('-','').isdigit() else 0.0
                                        obtained_marks = float(score_line) if score_line.replace('.','').replace('-','').isdigit() else 0.0
                                        
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




#helper function for parsing timetable data
def parse_timetable(html_content: str) -> Dict[str, Any]:
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
    unique_courses=[]
    
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
            #check if same code already edit before adding:
            if course['course_code'] not in unique_courses:
                data['total_credits'] += credit_val
                unique_courses.append(course['course_code'])
            
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
