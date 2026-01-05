#this will be used when there is no attendance data returned from the scraper and we have timetable data

def generate_mock_attendance_from_timetable(timetable_data):
    """
    Transforms actual timetable data into an attendance format 
    with all hours and percentages set to zero.
    """
    if not timetable_data or "courses" not in timetable_data:
        return None

    student_info_raw = timetable_data.get("student_info", {})
    courses_list = timetable_data.get("courses", [])

    mock_courses = {}
    mock_marks = {}

    for course in courses_list:
        # Standardize naming: e.g., 'Lab Based Theory' -> 'Theory'
        raw_type = course.get("course_type", "Theory")
        category = "Practical" if "Practical" in raw_type or "Lab" in raw_type else "Theory"
        
        # Course Key format: 21CSC302JRegularTheory
        course_key = f"{course['course_code']}Regular{category}"
        
        # 1. Map Attendance (Setting all values to 0)
        mock_courses[course_key] = {
            "course_title": course.get("course_title"),
            "category": category,
            "faculty_name": course.get("faculty_name"),
            "slot": course.get("slot"),
            "room_no": course.get("room_no"),
            "hours_conducted": 0,
            "hours_absent": 0,
            "attendance_percentage": 0.0
        }

        # 2. Map Marks (Empty tests list to reflect no exams conducted yet)
        marks_key = f"{course['course_code']}{category}"
        mock_marks[marks_key] = {
            "course_type": category,
            "tests": []
        }

    return {
        "student_info": {
            "registration_number": student_info_raw.get("registration_number"),
            "name": student_info_raw.get("name"),
            "program": student_info_raw.get("program"),
            "department": student_info_raw.get("department"),
            "semester": student_info_raw.get("semester"),
            "batch": student_info_raw.get("batch"),
        },
        "attendance": {
            "courses": mock_courses,
            "overall_attendance": 0.0,
            "total_hours_conducted": 0,
            "total_hours_absent": 0
        },
        "marks": mock_marks,
        "summary": {},
    }