import re
from typing import Dict, Optional, Any, List
from bs4 import BeautifulSoup


def safe_float(val: Any, default: float = 0.0) -> float:
    """Safely parse float values from strings that may contain spaces, %, or hyphens."""
    if val is None:
        return default
    try:
        cleaned = str(val).strip().replace('%', '').replace('-', '')
        return float(cleaned)
    except (ValueError, TypeError):
        return default


def safe_int(val: Any, default: int = 0) -> int:
    """Safely parse integer values from strings that may contain whitespace or decimals."""
    if val is None:
        return default
    try:
        cleaned = str(val).strip().split('.')[0]
        return int(cleaned)
    except (ValueError, TypeError):
        return default


def decode_page_sanitizer(html_content: str) -> Optional[str]:
    """
    Decodes SRM's escaped HTML from pageSanitizer.sanitize() wrapper or raw HTML.
    Supports flexible whitespace, multiple quote types, and fallback to direct HTML.
    """
    if not html_content or not isinstance(html_content, str):
        return None

    # Check for pageSanitizer.sanitize('...') or pageSanitizer.sanitize("...")
    match = re.search(r"pageSanitizer\.sanitize\s*\(\s*(['\"])(.*?)\1\s*\)", html_content, re.DOTALL)
    
    if match:
        escaped_html = match.group(2)
        # Unescape JS sequences
        # Handle \xNN hex escapes
        html_decoded = re.sub(
            r'\\x([0-9a-fA-F]{2})',
            lambda m: chr(int(m.group(1), 16)),
            escaped_html
        )
        html_decoded = html_decoded.replace("\\'", "'")
        html_decoded = html_decoded.replace('\\"', '"')
        html_decoded = html_decoded.replace('\\/', '/')
        html_decoded = html_decoded.replace('\\-', '-')
        html_decoded = html_decoded.replace('\\n', '\n')
        html_decoded = html_decoded.replace('\\t', '\t')
        html_decoded = html_decoded.replace('\\r', '\r')
        html_decoded = html_decoded.replace('\\\\', '')
        return html_decoded

    # Fallback: if already raw HTML containing table or body elements
    if "<table" in html_content.lower() or "<tr" in html_content.lower() or "<body" in html_content.lower():
        return html_content

    return None


def parse_attendance(html_content: str) -> Dict[str, Any]:
    """Parse attendance HTML to structured JSON matching desired format"""
    
    html_decoded = decode_page_sanitizer(html_content)
    if not html_decoded:
        return {"error": "Could not parse HTML"}
    
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
    
    # 1. Parse student information from table rows
    info_rows = soup.find_all('tr')
    for row in info_rows:
        cells = row.find_all('td')
        if len(cells) >= 2:
            key_text = cells[0].get_text(strip=True).replace(':', '').strip()
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
                    data['student_info']['enrollment_status'] = parts[0].strip()
                    data['student_info']['enrollment_date'] = parts[1].strip()
            elif key_text == 'Photo-ID':
                img_tag = cells[1].find('img')
                if img_tag and img_tag.get('src'):
                    data['student_info']['photo_url'] = img_tag.get('src')
    
    # Fallback student info extraction from text if needed
    full_text = soup.get_text(separator=' ')
    if not data['student_info'].get('registration_number'):
        reg_m = re.search(r'Registration\s*Number\s*:\s*([A-Za-z0-9]+)', full_text, re.IGNORECASE)
        if reg_m:
            data['student_info']['registration_number'] = reg_m.group(1).strip()
    if not data['student_info'].get('name'):
        name_m = re.search(r'Name\s*:\s*([a-zA-Z\s]+?)(?:Program|Department|$)', full_text, re.IGNORECASE)
        if name_m:
            data['student_info']['name'] = name_m.group(1).strip()
    if not data['student_info'].get('semester'):
        sem_m = re.search(r'Semester\s*:\s*(\d+)', full_text, re.IGNORECASE)
        if sem_m:
            data['student_info']['semester'] = sem_m.group(1).strip()
    if not data['student_info'].get('batch'):
        batch_m = re.search(r'Batch\s*:\s*(\d+)', full_text, re.IGNORECASE)
        if batch_m:
            data['student_info']['batch'] = batch_m.group(1).strip()
    if not data['student_info'].get('department'):
        dept_m = re.search(r'Department\s*:\s*([-a-zA-Z\s()]+?)(?:Specialization|Semester|$)', full_text, re.IGNORECASE)
        if dept_m:
            data['student_info']['department'] = dept_m.group(1).strip()
    if not data['student_info'].get('program'):
        prog_m = re.search(r'Program\s*:\s*([a-zA-Z\.\s]+?)(?:Department|$)', full_text, re.IGNORECASE)
        if prog_m:
            data['student_info']['program'] = prog_m.group(1).strip()

    # 2. Parse attendance courses with 3-tier resilient discovery
    attendance_table = None

    # Strategy 1: Table with bgcolor="#FAFAD2" (case-insensitive)
    for tbl in soup.find_all('table'):
        bgcolor = tbl.get('bgcolor', '')
        style = tbl.get('style', '')
        if '#fafad2' in bgcolor.lower() or '#fafad2' in style.lower():
            attendance_table = tbl
            break

    # Strategy 2: Find table by header content
    if not attendance_table:
        for tbl in soup.find_all('table'):
            first_tr = tbl.find('tr')
            if first_tr:
                header_text = first_tr.get_text().lower()
                if 'course code' in header_text and 'conducted' in header_text and 'absent' in header_text:
                    attendance_table = tbl
                    break

    # Strategy 3: Find largest table with numeric columns (conducted/absent)
    if not attendance_table:
        best_tbl = None
        best_score = 0
        for tbl in soup.find_all('table'):
            trs = tbl.find_all('tr')
            if len(trs) < 2:
                continue
            data_row = trs[1]
            tds = data_row.find_all('td')
            if len(tds) >= 7:
                numeric_cells = sum(1 for td in tds if td.get_text(strip=True).isdigit())
                score = len(trs) * numeric_cells
                if score > best_score:
                    best_score = score
                    best_tbl = tbl
        if best_tbl and best_score > 0:
            attendance_table = best_tbl

    if attendance_table:
        rows = attendance_table.find_all('tr')[1:]  # Skip header
        total_conducted = 0
        total_absent = 0
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 8:
                course_code_raw = cells[0].get_text(separator='\n', strip=True)
                course_code_parts = [p.strip() for p in course_code_raw.split('\n') if p.strip()]
                if not course_code_parts:
                    continue
                course_code = course_code_parts[0].split()[0]
                
                # Category (cells[2])
                category = cells[2].get_text(strip=True) if len(cells) > 2 else 'Theory'

                # Create unique key using course_code + category
                course_key = course_code + category
                
                hours_conducted = safe_int(cells[6].get_text(strip=True)) if len(cells) > 6 else 0
                hours_absent = safe_int(cells[7].get_text(strip=True)) if len(cells) > 7 else 0
                
                total_conducted += hours_conducted
                total_absent += hours_absent
                
                # Percentage
                percentage_text = cells[8].get_text(strip=True) if len(cells) > 8 else ''
                pct = safe_float(percentage_text)
                if pct == 0.0 and hours_conducted > 0:
                    pct = round(((hours_conducted - hours_absent) / hours_conducted) * 100, 2)

                data['attendance']['courses'][course_key] = {
                    'course_title': cells[1].get_text(strip=True) if len(cells) > 1 else '',
                    'category': category,
                    'faculty_name': cells[3].get_text(strip=True).split('(')[0].strip() if len(cells) > 3 else '',
                    'slot': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                    'room_no': cells[5].get_text(strip=True) if len(cells) > 5 else '',
                    'hours_conducted': hours_conducted,
                    'hours_absent': hours_absent,
                    'attendance_percentage': pct
                }
        
        # Calculate overall attendance
        if total_conducted > 0:
            data['attendance']['overall_attendance'] = round(
                ((total_conducted - total_absent) / total_conducted) * 100, 2
            )
        data['attendance']['total_hours_conducted'] = total_conducted
        data['attendance']['total_hours_absent'] = total_absent
    
    # 3. Parse internal marks with resilient table & cell discovery
    marks_table = None
    for tbl in soup.find_all('table'):
        tbl_text = tbl.get_text()
        if 'Course Code' in tbl_text and ('Test Performance' in tbl_text or '/' in tbl_text):
            if tbl.find_all('tr') and len(tbl.find_all('tr')) > 1:
                marks_table = tbl
                break

    if not marks_table:
        for tbl in soup.find_all('table'):
            if tbl.find('td') and tbl.find('td').find('table'):
                if any('/' in strong.get_text() for strong in tbl.find_all('strong')):
                    marks_table = tbl
                    break

    if marks_table:
        rows = marks_table.find_all('tr')[1:]  # Skip header
        for row in rows:
            cells = row.find_all('td')
            if len(cells) >= 3:
                course_raw = cells[0].get_text(separator='\n', strip=True)
                course_parts = [p.strip() for p in course_raw.split('\n') if p.strip()]
                if not course_parts:
                    continue
                # Extract course code (e.g. "21CSC302J" from "21CSC302J\nRegular")
                course_code = course_parts[0].split()[0]
                
                course_type = cells[1].get_text(strip=True)
                if not course_type:
                    course_type = "Theory"
                
                marks_key = course_code + course_type
                
                performance_cell = cells[2]
                tests = []
                
                # Check for sub-tables or multiple cells
                inner_table = performance_cell.find('table')
                test_cells = inner_table.find_all('td') if inner_table else [performance_cell]
                
                for cell in test_cells:
                    strong = cell.find('strong')
                    test_name = None
                    max_marks = 0.0
                    obtained_marks = 0.0
                    
                    if strong and '/' in strong.get_text():
                        strong_text = strong.get_text(strip=True)
                        parts = strong_text.split('/')
                        test_name = parts[0].strip()
                        max_marks = safe_float(parts[1])
                        remaining_text = cell.get_text(separator=' ', strip=True).replace(strong_text, '').strip()
                        float_match = re.search(r'[-+]?\d*\.?\d+', remaining_text)
                        if float_match:
                            obtained_marks = safe_float(float_match.group(0))
                    else:
                        text = cell.get_text(separator='\n', strip=True)
                        lines = [l.strip() for l in text.split('\n') if l.strip()]
                        for line in lines:
                            if '/' in line:
                                parts = line.split('/')
                                test_name = parts[0].strip()
                                max_marks = safe_float(parts[1])
                            else:
                                float_match = re.search(r'[-+]?\d*\.?\d+', line)
                                if float_match and test_name:
                                    obtained_marks = safe_float(float_match.group(0))
                    
                    if test_name and max_marks > 0:
                        pct = round((obtained_marks / max_marks) * 100, 2)
                        tests.append({
                            'test_name': test_name,
                            'obtained_marks': obtained_marks,
                            'max_marks': max_marks,
                            'percentage': pct
                        })
                
                if tests:
                    data['marks'][marks_key] = {
                        'course_type': course_type,
                        'tests': tests
                    }
    
    return data


def parse_timetable(html_content: str) -> Dict[str, Any]:
    """Parse timetable HTML to structured JSON with course information"""
    
    html_decoded = decode_page_sanitizer(html_content)
    if not html_decoded:
        return {"error": "Could not parse HTML"}
    
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
    
    # 1. Parse student information
    all_tables = soup.find_all('table')
    for table in all_tables:
        rows = table.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            for i in range(0, len(cells)-1, 2):
                if i+1 >= len(cells):
                    break
                label = cells[i].get_text(strip=True).replace(':', '').strip()
                value = cells[i+1].get_text(separator=' ', strip=True)
                value = re.sub(r'\s+', ' ', value).strip()
                
                if 'Registration Number' in label:
                    data['student_info']['registration_number'] = value
                elif label == 'Name':
                    data['student_info']['name'] = value
                elif 'Batch' in label:
                    data['student_info']['batch'] = value.split("/")[-1].strip()
                elif label == 'Mobile':
                    data['student_info']['mobile'] = value
                elif label == 'Program':
                    data['student_info']['program'] = value
                elif 'Department' in label:
                    data['student_info']['department'] = value
                elif label == 'Semester':
                    data['student_info']['semester'] = value

    # Fallback student info from text
    full_text = soup.get_text(separator=' ')
    if not data['student_info']['registration_number']:
        m = re.search(r'Registration\s*Number\s*:\s*([A-Za-z0-9]+)', full_text, re.IGNORECASE)
        if m:
            data['student_info']['registration_number'] = m.group(1).strip()
    if not data['student_info']['name']:
        m = re.search(r'Name\s*:\s*([a-zA-Z\s]+?)(?:Program|Department|$)', full_text, re.IGNORECASE)
        if m:
            data['student_info']['name'] = m.group(1).strip()
    if not data['student_info']['batch']:
        m = re.search(r'Batch\s*:\s*(\d+)', full_text, re.IGNORECASE)
        if m:
            data['student_info']['batch'] = m.group(1).strip()
    if not data['student_info']['semester']:
        m = re.search(r'Semester\s*:\s*(\d+)', full_text, re.IGNORECASE)
        if m:
            data['student_info']['semester'] = m.group(1).strip()
    
    # 2. Parse course data (using DOM table parsing with regex fallback)
    unique_courses = []
    
    course_table = soup.find('table', class_='course_tbl')
    if not course_table:
        for tbl in all_tables:
            txt = tbl.get_text().lower()
            if 'course code' in txt and 'credit' in txt and 'slot' in txt:
                course_table = tbl
                break

    if course_table:
        rows = course_table.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) >= 10:
                s_no_text = tds[0].get_text(strip=True)
                if not s_no_text.isdigit():
                    continue  # skip header row
                
                s_no = s_no_text
                course_code = tds[1].get_text(strip=True)
                course_title = tds[2].get_text(strip=True)
                credit_text = tds[3].get_text(strip=True)
                credit_val = safe_int(credit_text, 0)
                regn_type = tds[4].get_text(strip=True) if len(tds) > 4 else ''
                category = tds[5].get_text(strip=True) if len(tds) > 5 else ''
                course_type = tds[6].get_text(strip=True) if len(tds) > 6 else ''
                faculty_name = tds[7].get_text(strip=True) if len(tds) > 7 else ''
                slot = tds[8].get_text(strip=True) if len(tds) > 8 else ''
                room_no = tds[9].get_text(strip=True) if len(tds) > 9 else ''
                academic_year = tds[10].get_text(strip=True) if len(tds) > 10 else ''
                
                course = {
                    's_no': s_no,
                    'course_code': course_code,
                    'course_title': course_title,
                    'credit': credit_val,
                    'regn_type': regn_type,
                    'category': category,
                    'course_type': course_type,
                    'faculty_name': faculty_name,
                    'slot': slot,
                    'room_no': room_no,
                    'academic_year': academic_year
                }
                data['courses'].append(course)
                if course_code not in unique_courses:
                    data['total_credits'] += credit_val
                    unique_courses.append(course_code)

    # Fallback to regex if table finding found no courses
    if not data['courses']:
        course_pattern = r'<td>(\d+)</td><td>([^<]+)</td><td>([^<]+)</td><td>(\d+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td>([^<]+)</td><td[^>]*>([^<]+)</td><td>([^<]*)</td><td>([^<]+)</td>'
        courses_found = re.findall(course_pattern, html_decoded)
        for course_data in courses_found:
            try:
                s_no, course_code, course_title, credit, regn_type, category, course_type, faculty_name, slot, room_no, academic_year = course_data
                credit_val = safe_int(credit, 0)
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
                if course['course_code'] not in unique_courses:
                    data['total_credits'] += credit_val
                    unique_courses.append(course['course_code'])
            except Exception:
                continue
    
    # 3. Parse advisors
    for table in all_tables:
        cells = table.find_all('td', {'align': 'center'})
        if not cells:
            cells = table.find_all('td')
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
