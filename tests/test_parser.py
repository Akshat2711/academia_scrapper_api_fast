import pytest
from utils.parser import decode_page_sanitizer, parse_attendance, parse_timetable, safe_float, safe_int


def test_decode_page_sanitizer_variations():
    # 1. Standard single quote
    h1 = "<script>innerHTML = pageSanitizer.sanitize('<table><tr><td>Test</td></tr></table>');</script>"
    assert "<table>" in decode_page_sanitizer(h1)

    # 2. Double quote
    h2 = '<script>innerHTML = pageSanitizer.sanitize("<table><tr><td>Test</td></tr></table>");</script>'
    assert "<table>" in decode_page_sanitizer(h2)

    # 3. No spaces around equals
    h3 = "<script>document.getElementById('p').innerHTML=pageSanitizer.sanitize('<table><tr><td>Test</td></tr></table>');</script>"
    assert "<table>" in decode_page_sanitizer(h3)

    # 4. Function wrapper
    h4 = "<script>render(pageSanitizer.sanitize('<table><tr><td>Test</td></tr></table>'));</script>"
    assert "<table>" in decode_page_sanitizer(h4)

    # 5. Hex escaped characters
    h5 = r"<script>pageSanitizer.sanitize('<table><tr><td>Hello\x20World</td></tr></table>');</script>"
    assert "Hello World" in decode_page_sanitizer(h5)

    # 6. Raw HTML without pageSanitizer
    h6 = "<html><body><table><tr><td>Direct</td></tr></table></body></html>"
    assert "Direct" in decode_page_sanitizer(h6)

    # 7. Empty or invalid string
    assert decode_page_sanitizer("") is None
    assert decode_page_sanitizer("no html or sanitizer here") is None


def test_parse_attendance_student_info():
    html = r"""<script>
    innerHTML = pageSanitizer.sanitize('<table>
        <tr><td>Registration Number :</td><td>RA2111003010001</td></tr>
        <tr><td>Name :</td><td>John Doe</td></tr>
        <tr><td>Program :</td><td>B.Tech</td></tr>
        <tr><td>Department :</td><td>Computer Science and Engineering</td></tr>
        <tr><td>Semester :</td><td>6</td></tr>
        <tr><td>Batch :</td><td>1</td></tr>
    </table><table bgcolor="#FAFAD2">
        <tr><td>Course Code</td><td>Course Title</td><td>Category</td><td>Faculty</td><td>Slot</td><td>Room</td><td>Hours Conducted</td><td>Hours Absent</td><td>Attendance %</td></tr>
        <tr><td>21CSC302J\nRegular</td><td>Database Systems</td><td>Theory</td><td>Dr. Smith(1001)</td><td>A1</td><td>UB601</td><td>30</td><td>3</td><td>90.00</td></tr>
    </table>');
    </script>"""
    data = parse_attendance(html)
    assert "error" not in data
    assert data["student_info"]["registration_number"] == "RA2111003010001"
    assert data["student_info"]["name"] == "John Doe"
    assert data["student_info"]["program"] == "B.Tech"
    assert data["student_info"]["semester"] == "6"
    assert data["student_info"]["batch"] == "1"


def test_parse_attendance_table_discovery_variations():
    # 1. Lowercase bgcolor #fafad2
    html_lower = r"""<script>
    pageSanitizer.sanitize('<table bgcolor="#fafad2">
        <tr><td>Course Code</td><td>Course Title</td><td>Category</td><td>Faculty</td><td>Slot</td><td>Room</td><td>Hours Conducted</td><td>Hours Absent</td><td>Attendance %</td></tr>
        <tr><td>21CSC301T</td><td>Compiler Design</td><td>Theory</td><td>Prof. Alan</td><td>B1</td><td>UB602</td><td>20</td><td>2</td><td>90.00</td></tr>
    </table>');
    </script>"""
    d1 = parse_attendance(html_lower)
    assert "21CSC301TTheory" in d1["attendance"]["courses"]
    assert d1["attendance"]["courses"]["21CSC301TTheory"]["hours_conducted"] == 20
    assert d1["attendance"]["courses"]["21CSC301TTheory"]["hours_absent"] == 2

    # 2. Header-based discovery without bgcolor
    html_header = r"""<script>
    pageSanitizer.sanitize('<table class="custom-attendance">
        <tr><td>Course Code</td><td>Course Title</td><td>Category</td><td>Faculty</td><td>Slot</td><td>Room</td><td>Conducted</td><td>Absent</td><td>%</td></tr>
        <tr><td>21CSC303J</td><td>Web Tech</td><td>Practical</td><td>Prof. Eva</td><td>C1</td><td>UB603</td><td>40</td><td>4</td><td>90.00</td></tr>
    </table>');
    </script>"""
    d2 = parse_attendance(html_header)
    assert "21CSC303JPractical" in d2["attendance"]["courses"]
    assert d2["attendance"]["courses"]["21CSC303JPractical"]["hours_conducted"] == 40
    assert d2["attendance"]["courses"]["21CSC303JPractical"]["hours_absent"] == 4


def test_parse_marks_complete():
    html_marks = r"""<script>
    innerHTML = pageSanitizer.sanitize('<table bgcolor="#FAFAD2">
        <tr><td>Course Code</td><td>Course Title</td><td>Category</td><td>Faculty</td><td>Slot</td><td>Room</td><td>Hours Conducted</td><td>Hours Absent</td><td>Attendance %</td></tr>
        <tr><td>21CSC302J\nRegular</td><td>Database Systems</td><td>Theory</td><td>Dr. Smith</td><td>A1</td><td>UB601</td><td>30</td><td>3</td><td>90.00</td></tr>
    </table>
    <table border="1">
        <tr><td>Course Code</td><td>Course Type</td><td>Test Performance</td></tr>
        <tr>
            <td>21CSC302J\nRegular</td>
            <td>Theory</td>
            <td>
                <table>
                    <tr>
                        <td><strong>CLA-1/15.00</strong> 14.50</td>
                        <td><strong>CLA-2/15.00</strong> 13.00</td>
                        <td><strong>FT-I/5.00</strong> 5.00</td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>');
    </script>"""
    res = parse_attendance(html_marks)
    assert "error" not in res
    marks = res["marks"]
    assert "21CSC302JTheory" in marks
    course_marks = marks["21CSC302JTheory"]
    assert course_marks["course_type"] == "Theory"
    tests = course_marks["tests"]
    assert len(tests) == 3
    assert tests[0]["test_name"] == "CLA-1"
    assert tests[0]["max_marks"] == 15.0
    assert tests[0]["obtained_marks"] == 14.5
    assert tests[0]["percentage"] == 96.67
    assert tests[2]["test_name"] == "FT-I"
    assert tests[2]["max_marks"] == 5.0
    assert tests[2]["obtained_marks"] == 5.0
    assert tests[2]["percentage"] == 100.0


def test_parse_timetable_and_advisors():
    html_tt = r"""<script>
    pageSanitizer.sanitize('<table>
        <tr><td>Registration Number :</td><td>RA2111003010001</td><td>Name :</td><td>John Doe</td></tr>
        <tr><td>Combo / Batch :</td><td>1 / 2</td><td>Semester :</td><td>6</td></tr>
    </table>
    <table class="course_tbl">
        <tr><th>S.No</th><th>Course Code</th><th>Course Title</th><th>Credit</th><th>Regn. Type</th><th>Category</th><th>Course Type</th><th>Faculty</th><th>Slot</th><th>Room</th><th>Academic Year</th></tr>
        <tr><td>1</td><td>21CSC302J</td><td>Database Systems</td><td>4</td><td>Regular</td><td>Departmental Core</td><td>Theory</td><td>Dr. Smith</td><td>A1</td><td>UB601</td><td>2024-25</td></tr>
    </table>
    <table>
        <tr>
            <td align="center">
                Dr. Alan Turing<br>Faculty Advisor<br>alan@srmist.edu.in<br>9876543210
            </td>
            <td align="center">
                Dr. Grace Hopper<br>Academic Advisor<br>grace@srmist.edu.in<br>9123456780
            </td>
        </tr>
    </table>');
    </script>"""
    tt = parse_timetable(html_tt)
    assert "error" not in tt
    assert tt["student_info"]["registration_number"] == "RA2111003010001"
    assert tt["student_info"]["name"] == "John Doe"
    assert tt["student_info"]["batch"] == "2"
    assert len(tt["courses"]) == 1
    assert tt["courses"][0]["course_code"] == "21CSC302J"
    assert tt["courses"][0]["credit"] == 4
    assert tt["total_credits"] == 4
    assert "faculty_advisor" in tt["advisors"]
    assert tt["advisors"]["faculty_advisor"]["name"] == "Dr. Alan Turing"
    assert tt["advisors"]["faculty_advisor"]["email"] == "alan@srmist.edu.in"
    assert tt["advisors"]["academic_advisor"]["name"] == "Dr. Grace Hopper"


def test_malformed_html_returns_error():
    res = parse_attendance("invalid content without any html or sanitizer")
    assert "error" in res
    assert res["error"] == "Could not parse HTML"
